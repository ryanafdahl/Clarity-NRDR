"""Protocol v3 integration contracts shared by both Clarity Pilot deployments."""
import unittest
from unittest import mock

import numpy as np

from jetlink.spec import ModelSpec
from openpilot.sunnypilot.accelerators.jetlink.model_state import JetlinkModelState


class ProtocolV3Test(unittest.TestCase):
  def setUp(self):
    spec = ModelSpec(sha256='test', nbytes=1, frame_skip=4, checkpoint=None,
                     input_shapes={'img': (1, 12, 128, 256), 'big_img': (1, 12, 128, 256),
                                   'features_buffer': (1, 32, 2), 'desire_pulse': (1, 32, 8),
                                   'traffic_convention': (1, 2), 'action_t': (1, 2)},
                     output_shapes={'outputs': (1, 4)}, output_slices={'hidden_state': slice(2, 4)})
    self.client = mock.Mock(last_timings=(0, 0, 0))
    self.client.t.last_receive = {}
    self.client.infer_end.return_value = np.array([1, 2, 0, 0], dtype=np.float32)
    self.model = JetlinkModelState(1928, 1208, self.client, spec, warp=object())
    self.model.parser = mock.Mock()
    self.model.parser.parse_outputs.return_value = {}

  def run_frame(self):
    bufs = {key: np.zeros(8, dtype=np.uint8) for key in ('img', 'big_img')}
    transforms = {key: np.eye(3, dtype=np.float32) for key in bufs}
    inputs = {'desire_pulse': np.array([0, 1, 0, 0, 0, 0, 0, 0], dtype=np.float32),
              'traffic_convention': np.array([1, 0], dtype=np.float32),
              'action_t': np.array([.2, .4], dtype=np.float32)}
    warped = mock.Mock()
    warped.data.return_value = b'warped'
    with mock.patch('openpilot.sunnypilot.accelerators.jetlink.model_state.Tensor.from_blob'), \
         mock.patch('openpilot.sunnypilot.accelerators.jetlink.model_state.warp_cache.call_warp', return_value=warped):
      return self.model.run(bufs, transforms, inputs)

  def test_scalar_views_have_no_client_owned_recurrent_state(self):
    self.assertNotIn('prev_feat', self.model.npy)
    self.assertEqual(self.model.packed.size, 12)
    for name in ('desire', 'traffic_convention', 'action_t'):
      self.assertTrue(np.shares_memory(self.model.npy[name], self.model.packed))

  def test_frames_do_not_require_hidden_state_feedback(self):
    self.run_frame()
    self.assertTrue(self.client.infer_begin.call_args.kwargs['reset'])
    self.run_frame()
    self.assertFalse(self.client.infer_begin.call_args.kwargs['reset'])
    self.assertEqual(self.client.infer_begin.call_args.args[1].size, 12)
    self.assertEqual(self.model.parser.parse_outputs.call_count, 2)

  def test_raw_predictions_preserve_the_whole_client_output(self):
    self.client.infer_end.return_value = np.array([1, 2, 3, 4], dtype=np.float32)
    with mock.patch('openpilot.sunnypilot.accelerators.jetlink.model_state.SEND_RAW_PRED', '1'):
      output = self.run_frame()
    np.testing.assert_array_equal(output['raw_pred'], [1, 2, 3, 4])
    self.assertFalse(np.shares_memory(output['raw_pred'], self.client.infer_end.return_value))
