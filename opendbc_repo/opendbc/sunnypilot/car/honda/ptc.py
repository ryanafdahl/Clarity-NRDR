"""Clarity PTC profile adapted from nrdr/openpilot b3366b5.

Honda's version identifies a rack, not its calibration. A comma also marks
legacy mods, so activation requires explicit confirmation of installed PTC.
"""

import math
from dataclasses import dataclass

from opendbc.car.honda.values import CAR
from opendbc.sunnypilot.car.honda.values_ext import HondaFlagsSP

PTC_PARAM = "HondaClarityPtcFirmware"
PTC_FIRMWARE_SHA256 = "d4fe903bcf347495f4321be65a3c650c8c931f1650c3bef6443721da0dd80f7d"


def compatible_clarity_eps(CP) -> bool:
  if CP.brand != "honda" or CP.carFingerprint != CAR.HONDA_CLARITY:
    return False
  versions = [bytes(fw.fwVersion).rstrip(b"\0") for fw in CP.carFw if fw.ecu == "eps"]
  return bool(versions) and all(v in (b"39990-TRW,A020", b"39990,TRW,A020") for v in versions)


def configure_clarity_ptc(CP, CP_SP, params_dict) -> bool:
  if params_dict.get(PTC_PARAM) not in (True, 1, "1", b"1") or not compatible_clarity_eps(CP):
    return False
  CP_SP.flags |= HondaFlagsSP.CLARITY_PTC.value
  CP.lateralTuning.init("pid")
  CP.lateralTuning.pid.kpBP, CP.lateralTuning.pid.kpV = [0.0], [0.03]
  CP.lateralTuning.pid.kiBP, CP.lateralTuning.pid.kiV = [0.0], [0.01]
  CP.lateralTuning.pid.kf = 0.000012
  CP.lateralParams.torqueBP, CP.lateralParams.torqueV = [0, 3840], [0, 3840]
  # Preserve existing speed, standstill, longitudinal and safety policy.
  return True


def is_clarity_ptc(CP, CP_SP) -> bool:
  return compatible_clarity_eps(CP) and bool(CP_SP.flags & HondaFlagsSP.CLARITY_PTC.value)


@dataclass
class PtcDriverOverride:
  """NRDR fade-in, with immediate release of torque and LKAS on takeover."""

  ramp: float = 0.0

  def update(self, torque: float, active: bool, steering_pressed: bool, dt: float) -> tuple[float, bool]:
    if not active or steering_pressed or not math.isfinite(torque):
      self.ramp = 0.0
      return 0.0, False
    self.ramp = min(1.0, self.ramp + dt / 0.1)
    return max(-1.0, min(1.0, torque)) * self.ramp, True
