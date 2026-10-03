"""First-install selection never replaces a saved choice or fights cancellation."""
import asyncio
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

from openpilot.sunnypilot.models.initial_model import (
  INITIAL_SMALL_MODEL_REF, P_INITIALIZED, cancel_download, remember_small_model_choice,
)
from openpilot.sunnypilot.models.manager import ModelManagerSP


class FakeParams(dict):
  def get_bool(self, key):
    return bool(self.get(key))

  def put(self, key, value, **kwargs):
    self[key] = value

  put_bool = put

  def remove(self, key):
    self.pop(key, None)


class InitialModelTest(unittest.TestCase):
  def setUp(self):
    self.manager = ModelManagerSP.__new__(ModelManagerSP)
    self.params = FakeParams()
    params_patch = mock.patch.object(self.manager, 'params', self.params, create=True)
    params_patch.start()
    self.addCleanup(params_patch.stop)
    self.bundle = SimpleNamespace(ref=INITIAL_SMALL_MODEL_REF)
    self.manager.source_models = {'qcom': [self.bundle], 'chestnut': []}
    patcher = mock.patch('openpilot.sunnypilot.models.manager.get_selected_bundle', return_value=None)
    self.selected = patcher.start()
    self.addCleanup(patcher.stop)

  def test_fresh_install_queues_the_exact_release(self):
    self.manager._queue_initial_small_model()
    self.assertEqual(self.params['ModelManager_DownloadRef'], INITIAL_SMALL_MODEL_REF)
    self.assertFalse(self.params.get_bool(P_INITIALIZED))

  def test_waits_for_the_small_catalog(self):
    self.manager.source_models = {'qcom': [], 'chestnut': [self.bundle]}
    self.manager._queue_initial_small_model()
    self.assertNotIn('ModelManager_DownloadRef', self.params)

  def test_preserves_existing_selection_and_remembers_it(self):
    self.selected.return_value = object()
    self.manager._queue_initial_small_model()
    self.assertNotIn('ModelManager_DownloadRef', self.params)
    self.assertTrue(self.params.get_bool(P_INITIALIZED))
    self.selected.return_value = None
    self.manager._queue_initial_small_model()
    self.assertNotIn('ModelManager_DownloadRef', self.params)

  def test_preserves_queued_download(self):
    self.params['ModelManager_DownloadRef'] = 'other-model'
    self.manager._queue_initial_small_model()
    self.assertEqual(self.params['ModelManager_DownloadRef'], 'other-model')

  def test_failed_or_interrupted_initial_download_can_retry(self):
    self.manager._queue_initial_small_model()
    self.params.remove('ModelManager_DownloadRef')
    self.manager._queue_initial_small_model()
    self.assertEqual(self.params['ModelManager_DownloadRef'], INITIAL_SMALL_MODEL_REF)

  def test_cancel_opts_out_even_after_manager_restart(self):
    self.manager._queue_initial_small_model()
    cancel_download(self.params)
    self.manager._queue_initial_small_model()
    self.assertNotIn('ModelManager_DownloadRef', self.params)
    self.assertTrue(self.params.get_bool(P_INITIALIZED))

  def test_explicit_bundled_model_choice_stops_initial_download(self):
    self.manager._queue_initial_small_model()
    remember_small_model_choice(self.params)
    self.manager._queue_initial_small_model()
    self.assertNotIn('ModelManager_DownloadRef', self.params)

  def test_cancel_of_another_download_does_not_opt_out(self):
    self.params['ModelManager_DownloadRef'] = 'chestnut-model'
    cancel_download(self.params)
    self.manager._queue_initial_small_model()
    self.assertEqual(self.params['ModelManager_DownloadRef'], INITIAL_SMALL_MODEL_REF)

  def _download_fixture(self):
    self.manager._report_status = mock.Mock()
    self.manager._process_artifact = mock.AsyncMock()
    self.manager.chestnut_present = False
    self.params['ModelManager_DownloadRef'] = INITIAL_SMALL_MODEL_REF
    return SimpleNamespace(models=[SimpleNamespace(artifact=SimpleNamespace(fileName='model.pkl', downloadProgress=SimpleNamespace()))],
                           to_dict=lambda: {'ref': INITIAL_SMALL_MODEL_REF})

  def test_download_success_marks_first_install_complete(self):
    bundle = self._download_fixture()
    with tempfile.TemporaryDirectory() as destination, \
         mock.patch('openpilot.sunnypilot.models.manager.get_active_bundle', return_value=bundle):
      asyncio.run(self.manager._download_bundle(bundle, destination, 'qcom'))
    self.assertTrue(self.params.get_bool(P_INITIALIZED))
    self.assertEqual(self.params['ModelManager_ActiveBundle'], {'ref': INITIAL_SMALL_MODEL_REF})

  def test_failed_download_does_not_complete_initial_selection(self):
    bundle = self._download_fixture()
    self.manager._process_artifact.side_effect = RuntimeError('hash mismatch')
    with tempfile.TemporaryDirectory() as destination, self.assertRaisesRegex(RuntimeError, 'hash mismatch'):
      asyncio.run(self.manager._download_bundle(bundle, destination, 'qcom'))
    self.assertFalse(self.params.get_bool(P_INITIALIZED))
    self.assertNotIn('ModelManager_ActiveBundle', self.params)
