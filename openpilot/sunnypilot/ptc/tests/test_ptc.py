import math
from types import SimpleNamespace

import numpy as np
import pytest

from opendbc.car import Bus, gen_empty_fingerprint, structs
from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.values import CAR, DBC
from opendbc.car.honda.carcontroller import CarController
from opendbc.car.honda.carstate import CarState
from opendbc.car.vehicle_model import VehicleModel
from opendbc.can import CANParser
from opendbc.sunnypilot.car.interfaces import setup_interfaces
from opendbc.sunnypilot.car.honda.ptc import PTC_PARAM, configure_clarity_ptc, is_clarity_ptc
from opendbc.sunnypilot.car.honda.values_ext import HondaFlagsSP
from openpilot.sunnypilot.ptc.latcontrol import ClarityPtcPID


def params(version=b"39990-TRW,A020\0\0", car=CAR.HONDA_CLARITY):
  fw = [] if version is None else [structs.CarParams.CarFw(ecu="eps", fwVersion=version)]
  fingerprint = gen_empty_fingerprint()
  cp = CarInterface.get_params(car, fingerprint, fw, False, False, False)
  cp.carFw = fw
  sp = CarInterface.get_params_sp(cp, car, fingerprint, fw, False, False, False)
  return cp, sp


@pytest.mark.parametrize("version", [b"39990-TRW,A020\0\0", b"39990,TRW,A020\0\0"])
def test_ptc_startup(version):
  cp, sp = params(version)
  safety = [(s.safetyModel, s.safetyParam) for s in cp.safetyConfigs]
  previous = (cp.steerAtStandstill, cp.minSteerSpeed, cp.openpilotLongitudinalControl, sp.safetyParam)
  setup_interfaces(CarInterface, cp, sp, [{PTC_PARAM: True}])
  assert is_clarity_ptc(cp, sp)
  assert cp.lateralTuning.which() == "pid"
  assert list(cp.lateralParams.torqueBP) == [0, 3840]
  assert list(cp.lateralParams.torqueV) == [0, 3840]
  assert list(cp.lateralTuning.pid.kpV) == pytest.approx([0.03])
  assert list(cp.lateralTuning.pid.kiV) == pytest.approx([0.01])
  assert cp.lateralTuning.pid.kf == pytest.approx(0.000012)
  assert previous == (cp.steerAtStandstill, cp.minSteerSpeed, cp.openpilotLongitudinalControl, sp.safetyParam)
  assert safety == [(s.safetyModel, s.safetyParam) for s in cp.safetyConfigs]


@pytest.mark.parametrize("version,confirmed", [
  (None, True), (b"39990-TRW-A020\0\0", True), (b"39990-TRW,A010\0\0", True),
  (b"39990-TRW,A020-unexpected", True), (b"39990-TRW,A020\0\0", False),
])
def test_firmware_gate_preserves_original(version, confirmed):
  cp, sp = params(version)
  before = cp.to_dict()
  flags = sp.flags
  assert not configure_clarity_ptc(cp, sp, {PTC_PARAM: confirmed})
  assert cp.to_dict() == before
  assert sp.flags == flags


def test_non_clarity_and_conflicting_firmware_rejected():
  cp, sp = params(b"39990-TBA,A030\0\0", CAR.HONDA_CIVIC)
  assert not configure_clarity_ptc(cp, sp, {PTC_PARAM: True})
  cp, sp = params()
  cp.carFw = list(cp.carFw) + [structs.CarParams.CarFw(ecu="eps", fwVersion=b"39990-TRW-A020\0\0")]
  assert not configure_clarity_ptc(cp, sp, {PTC_PARAM: True})


@pytest.mark.parametrize("version,expected", [
  (b"39990-TRW-A020\0\0", [0, 2560]),
  (b"39990-TRW,A020\0\0", [0, 5760, 10240]),
  (b"39990,TRW,A020\0\0", [0, 5760, 15360]),
])
def test_legacy_maps(version, expected):
  cp, sp = params(version)
  setup_interfaces(CarInterface, cp, sp, [{PTC_PARAM: False}])
  assert list(cp.lateralParams.torqueBP) == expected
  assert not sp.flags & HondaFlagsSP.CLARITY_PTC


def ptc_controller():
  cp, sp = params()
  configure_clarity_ptc(cp, sp, {PTC_PARAM: True})
  ci = CarInterface(cp, sp)
  return cp, sp, ClarityPtcPID(cp, sp, ci, 0.01)


def state(speed=20.0, angle=0.0):
  return SimpleNamespace(vEgo=speed, steeringAngleDeg=angle, steeringRateDeg=0.0,
                         steeringPressed=False, leftBlinker=False, rightBlinker=False)


def update(controller, cp, cs, curvature=-0.001, active=True, limited=False):
  lp = SimpleNamespace(roll=0.0, angleOffsetDeg=0.0)
  vm = VehicleModel(cp)
  return controller.update(active, cs, vm, lp, limited, curvature, None, False, 0.2)


def test_geometry_roundtrip_and_left_right_symmetry():
  cp, _, controller = ptc_controller()
  for angle in np.linspace(-500, 500, 201):
    physical = controller.rack.linear_to_physical(angle)
    assert controller.measured_angle(physical) == pytest.approx(angle, abs=1e-8)
    assert physical == pytest.approx(-controller.rack.linear_to_physical(-angle))
  left = update(controller, cp, state(), -0.001)[0]
  controller.reset()
  right = update(controller, cp, state(), 0.001)[0]
  assert left == pytest.approx(-right)
  assert left > 0


def test_integrator_reset_takeover_and_inactive():
  cp, _, controller = ptc_controller()
  for _ in range(100):
    output, _, _ = update(controller, cp, state())
    assert math.isfinite(output) and abs(output) <= 1
  assert controller.pid.i > 0
  before = controller.pid.i
  update(controller, cp, state(), limited=True)
  assert controller.pid.i == before
  update(controller, cp, state(speed=1.0))
  assert controller.pid.i == 0
  cs = state()
  cs.steeringPressed = True
  assert update(controller, cp, cs)[0] == 0
  assert controller.pid.i == 0 and controller.output_filter.output == 0
  assert update(controller, cp, state(), active=False)[0] == 0


@pytest.mark.parametrize("torque", [-1.0, -0.5, 0.5, 1.0])
def test_actual_can_output_and_immediate_override(torque):
  cp, sp = params()
  configure_clarity_ptc(cp, sp, {PTC_PARAM: True})
  controller = CarController(DBC[cp.carFingerprint], cp, sp)
  cs = CarState(cp, sp)
  cs.out, _ = cs.update(cs.get_can_parsers(cp, sp))
  cs.out.vEgo = 20
  cs.v_cruise_factor = 1
  cs.is_metric = False
  cs.stock_brake = {"CHIME": 0}
  cc = structs.CarControl()
  cc.latActive = True
  cc.actuators.torque = torque
  cc_sp = structs.CarControlSP()
  parser = CANParser(DBC[cp.carFingerprint][Bus.pt], [("STEERING_CONTROL", 100)], 0)
  for frame in range(12):
    actuators, msgs = controller.update(cc.as_reader(), cc_sp, cs, frame * 10_000_000)
  parser.update([120_000_000, msgs])
  assert parser.vl["STEERING_CONTROL"]["STEER_TORQUE"] == pytest.approx(-torque * 3840, abs=1)
  assert parser.vl["STEERING_CONTROL"]["STEER_TORQUE_REQUEST"] == 1
  assert actuators.torque == pytest.approx(torque)
  cs.out.steeringPressed = True
  actuators, msgs = controller.update(cc.as_reader(), cc_sp, cs, 130_000_000)
  parser.update([130_000_000, msgs])
  assert parser.vl["STEERING_CONTROL"]["STEER_TORQUE"] == 0
  assert parser.vl["STEERING_CONTROL"]["STEER_TORQUE_REQUEST"] == 0
  assert actuators.torque == 0
  cs.out.steeringPressed = False
  cc.latActive = False
  actuators, msgs = controller.update(cc.as_reader(), cc_sp, cs, 140_000_000)
  assert actuators.torque == 0





def test_stock_takeover_threshold():
  cp, sp = params()
  configure_clarity_ptc(cp, sp, {PTC_PARAM: True})
  cs = CarState(cp, sp)
  parsers = cs.get_can_parsers(cp, sp)
  from opendbc.can import CANPacker
  packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
  for raw, pressed in [(1200, False), (1201, True), (-1201, True)]:
    msg = packer.make_can_msg("STEER_STATUS", 0, {"STEER_TORQUE_SENSOR": raw})
    parsers[Bus.pt].update([0, [msg]])
    out, _ = cs.update(parsers)
    assert out.steeringPressed == pressed


def test_can_release_on_nonfinite_request():
  from opendbc.sunnypilot.car.honda.ptc import PtcDriverOverride
  override = PtcDriverOverride()
  for invalid in (float("nan"), float("inf"), -float("inf")):
    assert override.update(invalid, True, False, 0.01) == (0.0, False)
    assert override.ramp == 0.0
