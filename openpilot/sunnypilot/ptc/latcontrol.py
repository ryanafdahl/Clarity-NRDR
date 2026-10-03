"""Matched Clarity PTC PID and firmware geometry, adapted from NRDR b3366b5.

Experimental tune learners, torque blending and live geometry changes are not
part of this profile. Driver takeover remains immediate at the stock threshold.
"""

import math
from types import SimpleNamespace

import numpy as np

from openpilot.cereal import log
from openpilot.common.filter_simple import FirstOrderFilter
from openpilot.selfdrive.controls.lib.latcontrol import LatControl
from openpilot.sunnypilot.ptc.honda_vgr import get_honda_vgr_profile
from openpilot.sunnypilot.ptc.integral_pid import IntegralScaledPIDController
from openpilot.sunnypilot.ptc.phase_detector import phase_with_latch
from openpilot.sunnypilot.ptc.torque_output_filter import HondaTorqueOutputFilter

MPH_TO_MS = 0.44704
OUTPUT_FILTER = SimpleNamespace(torque_lpf_enabled=True, lpf_tau_low=0.1, lpf_tau_standard=0.1, lpf_tau_highway=0.05)


class ClarityPtcPID(LatControl):
  def __init__(self, CP, CP_SP, CI, dt):
    super().__init__(CP, CP_SP, CI, dt)
    self.pid = IntegralScaledPIDController(
      (CP.lateralTuning.pid.kpBP, CP.lateralTuning.pid.kpV),
      (CP.lateralTuning.pid.kiBP, CP.lateralTuning.pid.kiV),
      pos_limit=self.steer_max, neg_limit=-self.steer_max, rate=1.0 / dt,
    )
    self.ff_factor = CP.lateralTuning.pid.kf
    self.get_steer_feedforward = CI.get_steer_feedforward_function()
    self.rack = get_honda_vgr_profile(CP)
    if self.rack is None:
      raise ValueError("PTC requires a supported Clarity EPS identity")
    self.previous_desired_angle = 0.0
    self.phase_direction = 0.0
    self.output_filter = HondaTorqueOutputFilter()
    self.center_taper = FirstOrderFilter(1.0, 0.25, dt)

  def reset(self):
    super().reset()
    self.pid.reset()
    self.output_filter.output = 0.0
    self.center_taper.x = 1.0
    self.previous_desired_angle = 0.0
    self.phase_direction = 0.0

  def measured_angle(self, angle):
    return self.rack.physical_to_linear(angle)

  def update(self, active, CS, VM, params, steer_limited_by_safety, desired_curvature,
             calibrated_pose, curvature_limited, lat_delay):
    pid_log = log.ControlsState.LateralPIDState.new_message()
    pid_log.steeringAngleDeg = float(CS.steeringAngleDeg)
    pid_log.steeringRateDeg = float(CS.steeringRateDeg)
    linear_desired = math.degrees(VM.get_steer_from_curvature(-desired_curvature, CS.vEgo, params.roll))
    desired_no_offset = self.rack.linear_to_physical(linear_desired)
    desired = desired_no_offset + params.angleOffsetDeg
    error = desired - CS.steeringAngleDeg
    pid_log.steeringAngleDesiredDeg = desired
    pid_log.angleError = error

    if not active or CS.steeringPressed:
      self.reset()
      self.previous_desired_angle = desired_no_offset
      pid_log.active = bool(active)
      return 0.0, desired, pid_log

    self.pid.update_lateral(
      error, feedforward=self.ff_factor * self.get_steer_feedforward(desired_no_offset, CS.vEgo),
      speed=CS.vEgo, i_scale=1.0, eps_modified=True, steer_limited=steer_limited_by_safety,
      steering_pressed=False, stiction_freeze=False,
    )
    # NRDR's default center boost: 50% near center, fading in above 50 mph.
    if CS.leftBlinker or CS.rightBlinker:
      self.center_taper.x = 0.0
      center_fade = 0.0
    else:
      center_fade = self.center_taper.update(1.0)
    angle_weight = float(np.clip(4.0 - abs(desired_no_offset), 0.0, 1.0))
    speed_weight = float(np.clip((CS.vEgo - 50.0 * MPH_TO_MS) / (5.0 * MPH_TO_MS), 0.0, 1.0))
    p_term = self.pid.p * (1.0 + angle_weight * 0.5 * center_fade * speed_weight)
    # Default NRDR low-speed rate damping; optional phase shaping is disabled.
    damping_fade = float(np.clip((30.0 * MPH_TO_MS - CS.vEgo) / (30.0 * MPH_TO_MS), 0.0, 1.0))
    phase, self.phase_direction = phase_with_latch(
      desired_no_offset, desired_no_offset - self.previous_desired_angle, CS.vEgo, self.phase_direction,
    )
    unwind_weight = float(np.clip(-phase / 0.5, 0.0, 1.0))
    angle_fade = float(np.clip((30.0 - abs(CS.steeringAngleDeg)) / 30.0, 0.0, 1.0))
    unwind_factor = 1.0 - unwind_weight + unwind_weight * angle_fade
    output = p_term + self.pid.i + self.pid.f - 0.003 * CS.steeringRateDeg * damping_fade * unwind_factor
    self.previous_desired_angle = desired_no_offset
    output = float(np.clip(output, -self.steer_max, self.steer_max))
    output = self.output_filter.update(output, active, CS.vEgo, OUTPUT_FILTER, self.dt)
    pid_log.active = True
    pid_log.p, pid_log.i, pid_log.f = float(p_term), float(self.pid.i), float(self.pid.f)
    pid_log.output = float(output)
    pid_log.saturated = bool(self._check_saturation(
      abs(output) >= self.steer_max - 1e-3, CS, steer_limited_by_safety, curvature_limited,
    ))
    return float(output), desired, pid_log
