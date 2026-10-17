"""API-3 handoff gating and the real warp format consumed by JetLink v0.8.7."""
import pickle
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np

from jetlink.openpilot.warp import Warps
from openpilot.sunnypilot import jetlink_adapter
from openpilot.sunnypilot.jetlink_adapter.compile_warp import capture


class TestControlGate(unittest.TestCase):
  def test_every_control_mode_and_missing_service_blocks_handoff(self):
    adapter = jetlink_adapter.Adapter.__new__(jetlink_adapter.Adapter)
    sm = mock.MagicMock()
    adapter._sm = sm
    for enabled, mads, alive, valid in [
      (False, False, True, True), (True, False, True, True),
      (False, True, True, True), (False, False, False, True),
      (False, False, True, False),
    ]:
      sm.all_alive.return_value, sm.all_valid.return_value = alive, valid
      values = {'carControl': SimpleNamespace(enabled=enabled),
                'carControlSP': SimpleNamespace(mads=SimpleNamespace(enabled=mads))}
      sm.__getitem__.side_effect = values.__getitem__
      self.assertEqual(adapter.in_control(), enabled or mads or not alive or not valid)
    sm.update.side_effect = RuntimeError('messaging unavailable')
    self.assertTrue(adapter.in_control())


class TestDrivingWarp(unittest.TestCase):
  def test_capture_loads_and_matches_the_existing_camera_graph(self):
    from tinygrad import Tensor
    from openpilot.selfdrive.modeld.compile_modeld import NV12Frame, make_warp
    from openpilot.system.camerad.cameras.nv12_info import get_nv12_info

    cam_w, cam_h, model_w, model_h = 16, 8, 8, 4
    warp = capture(cam_w, cam_h, model_w, model_h)
    with tempfile.TemporaryDirectory() as directory:
      path = Path(directory) / 'warp.pkl'
      path.write_bytes(pickle.dumps(warp))
      op = SimpleNamespace(warp_path=lambda *args: path)
      loaded = Warps(op).load(cam_w, cam_h, model_w, model_h)
    specs = loaded['input_specs']
    frames = np.random.default_rng(0).integers(0, 256, specs['input_frame'][0], dtype=np.uint8)
    transforms = np.stack([np.eye(3, dtype=np.float32)] * 2)
    transforms[1, 0, 2] = 1.0
    inputs = {'input_frame': Tensor(frames, device=specs['input_frame'][2]).realize(),
              'M_inv': Tensor(transforms, device=specs['M_inv'][2]).realize()}
    actual = loaded['run'](**inputs).numpy()
    original = make_warp(NV12Frame(cam_w, cam_h, *get_nv12_info(cam_w, cam_h)), model_w, model_h)
    expected = original(inputs['M_inv'][0], inputs['M_inv'][1], inputs['input_frame'][0], inputs['input_frame'][1]).numpy()
    np.testing.assert_array_equal(actual, expected)
