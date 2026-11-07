"""Jetlink's API4 index through the real adapter and model manager, with no network."""
from __future__ import annotations

import copy
import os
import time
import unittest
from unittest import mock

from jetlink.registry.index import NetworkError, parse_index

from openpilot.common.params import Params
from openpilot.common.test import OpenpilotTestCase
from openpilot.sunnypilot import jetlink_adapter
from openpilot.sunnypilot.jetlink_adapter import KEYS, MODES
from openpilot.sunnypilot.models import helpers, manager as manager_module
from openpilot.sunnypilot.models.fetcher import ModelFetcher, ModelParser
from openpilot.sunnypilot.models.helpers import REQUIRED_JSON_VERSION, resolve_bundle_by_ref, validate_active_bundles

V2, V3, OLD_V3 = 'a' * 40, 'e' * 40, 'd' * 40
V2_OID, V3_OID = '2' * 64, '3' * 64


def native_bundle(ref: str, name: str, *, big=True) -> dict:
  return {'ref': ref, 'index': 12, 'minimum_selector_version': str(REQUIRED_JSON_VERSION),
          'is_big': big, 'is_20hz': True, 'display_name': name, 'short_name': name[:4],
          'generation': '12', 'environment': 'development', 'runner': 'tinygrad',
          'build_time': '2026-09-25T00:00:00Z', 'overrides': {'folder': 'Master Models'},
          'models': [{'type': 'chunked', 'artifact': {'file_name': name + '.pkl',
                      'download_uri': {'url': 'https://example.invalid/model', 'sha256': '0' * 64}}}]}


NATIVE = {'bundles': [native_bundle(V2, 'Cinque Terre V2')]}
SMALL = {'bundles': [native_bundle('1' * 40, 'Pop V2', big=False)]}
INDEX = {'schema': 1, 'default': V2,
         'models': [{'ref': V2, 'oid': V2_OID, 'size': 766040736, 'name': 'Cinque Terre V2', 'short_name': 'CTMV2'},
                    {'ref': V3, 'oid': V3_OID, 'size': 766354845, 'name': 'Cinque Terre V3', 'short_name': 'CTV3M'}],
         'refs': {OLD_V3: {'oid': V3_OID, 'size': 766354845}},
         'onnx': {}}


def parsed(catalog):
  return ModelParser.parse_models(catalog)


def selected(ref=V2, name='Cinque Terre V2'):
  raw = parsed({'bundles': [native_bundle(ref, name)]})[0].to_dict()
  raw['status'] = 'downloaded'
  return raw


class IndexTest(OpenpilotTestCase):
  def setUp(self):
    super().setUp()
    self.params = Params()
    self.index_data = copy.deepcopy(INDEX)
    self.addCleanup(helpers._LAST_VALIDATED_RAW.clear)
    helpers._LAST_VALIDATED_RAW.clear()
    for patcher in (
      mock.patch.object(jetlink_adapter, '_bound', None),
      mock.patch('openpilot.selfdrive.modeld.helpers.chestnut_present', return_value=False),
      mock.patch.object(helpers, 'chestnut_present', return_value=False),
    ):
      patcher.start()
      self.addCleanup(patcher.stop)
    refresh = mock.patch('jetlink.openpilot.models.Models.refresh_index', autospec=True,
                         side_effect=lambda _: parse_index(copy.deepcopy(self.index_data)))
    self.refresh = refresh.start()
    self.addCleanup(refresh.stop)
    local_index = mock.patch('jetlink.openpilot.models.Models.index', autospec=True,
                             side_effect=lambda _: parse_index(copy.deepcopy(self.index_data)))
    self.local_index = local_index.start()
    self.addCleanup(local_index.stop)

  def catalog(self):
    result = jetlink_adapter.big_catalog(REQUIRED_JSON_VERSION)
    self.assertIsNotNone(result)
    return result

  def validate(self, catalog):
    validate_active_bundles(self.params, {'chestnut': parsed(catalog)})


class TestModelIndex(IndexTest):
  def test_the_index_is_the_big_list_at_this_builds_selector(self):
    catalog = self.catalog()
    self.assertEqual([b['ref'] for b in catalog['bundles']], [V2, V3])
    self.assertEqual([b.ref for b in parsed(catalog)], [V2, V3])
    self.assertTrue(all(b['models'] == [] for b in catalog['bundles']))
    self.assertTrue(all(int(b['minimum_selector_version']) == REQUIRED_JSON_VERSION for b in catalog['bundles']))

  def test_the_catalog_follows_hardware_while_the_link_is_off_or_on(self):
    for mode in MODES:
      self.params.put(KEYS.link, MODES.index(mode), block=True)
      for fitted in (False, True):
        with mock.patch('openpilot.selfdrive.modeld.helpers.chestnut_present', return_value=fitted), \
             mock.patch.object(jetlink_adapter, '_bound', None):
          self.assertEqual(jetlink_adapter.lists_big_models(), not fitted)

  def test_old_refs_resolve_only_to_the_same_onnx(self):
    self.assertEqual(jetlink_adapter.listed_ref(OLD_V3), V3)
    self.assertEqual(jetlink_adapter.listed_ref(V2), V2)
    self.assertIsNone(jetlink_adapter.listed_ref('f' * 40))

  def test_a_failed_index_fetch_has_no_catalog_to_replace_the_cache(self):
    self.refresh.side_effect = NetworkError('offline')
    self.assertIsNone(jetlink_adapter.big_catalog(REQUIRED_JSON_VERSION))


class TestFetcher(IndexTest):
  def setUp(self):
    super().setUp()
    self.fetcher = ModelFetcher(self.params)

  def test_index_fetch_never_requests_the_pinned_native_catalog(self):
    with mock.patch('openpilot.sunnypilot.models.fetcher.requests.get') as request:
      models = self.fetcher._fetch_and_cache_models('chestnut')
    self.assertEqual([b.ref for b in models], [V2, V3])
    request.assert_not_called()
    self.refresh.assert_called_once()
    self.assertIs(self.params.get(KEYS.catalog)[ModelFetcher.INDEX_KEY], True)

  def test_offline_keeps_the_cached_list_without_claiming_a_fresh_fetch(self):
    self.fetcher._fetch_and_cache_models('chestnut')
    before = self.params.get(KEYS.catalog)
    self.params.put('ModelManager_LastSyncTime_Chestnut', 0, block=True)
    self.refresh.side_effect = NetworkError('offline')
    with mock.patch('openpilot.sunnypilot.models.fetcher.requests.get') as request:
      result = self.fetcher.get_bundles_for_source('chestnut')
    self.assertEqual([b.ref for b in result], [V2, V3])
    self.assertEqual(self.params.get(KEYS.catalog), before)
    self.assertEqual(self.params.get('ModelManager_LastSyncTime_Chestnut'), 0)
    request.assert_not_called()

  def test_upgrade_offline_keeps_the_legacy_catalog(self):
    self.params.put(KEYS.catalog, {**NATIVE, 'extended': True}, block=True)
    self.params.put('ModelManager_LastSyncTime_Chestnut', 0, block=True)
    self.refresh.side_effect = NetworkError('offline')
    self.assertEqual([b.ref for b in self.fetcher.get_bundles_for_source('chestnut')], [V2])
    self.assertEqual(self.params.get(KEYS.catalog), {**NATIVE, 'extended': True})

  def test_a_real_chestnut_uses_its_native_artifact_catalog(self):
    response = mock.MagicMock(status_code=200)
    response.json.return_value = NATIVE
    with mock.patch('openpilot.selfdrive.modeld.helpers.chestnut_present', return_value=True), \
         mock.patch.object(jetlink_adapter, '_bound', None), \
         mock.patch('openpilot.sunnypilot.models.fetcher.requests.get', return_value=response) as request:
      result = self.fetcher._fetch_and_cache_models('chestnut')
    request.assert_called_once_with(ModelFetcher.MODEL_URL_CHESTNUT, timeout=10)
    self.refresh.assert_not_called()
    self.assertTrue(result[0].models)
    self.assertIs(self.params.get(KEYS.catalog)[ModelFetcher.INDEX_KEY], False)

  def test_small_model_fetch_never_asks_jetlink(self):
    response = mock.MagicMock(status_code=200)
    response.json.return_value = SMALL
    with mock.patch('openpilot.sunnypilot.models.fetcher.requests.get', return_value=response), \
         mock.patch.object(jetlink_adapter, 'lists_big_models') as asked, \
         mock.patch.object(jetlink_adapter, 'big_catalog') as indexed:
      result = self.fetcher._fetch_and_cache_models('qcom')
    self.assertEqual([b.ref for b in result], ['1' * 40])
    asked.assert_not_called()
    indexed.assert_not_called()

  def test_hardware_change_attempts_a_refetch_once_while_offline(self):
    self.params.put(KEYS.catalog, {**NATIVE, ModelFetcher.INDEX_KEY: False}, block=True)
    with mock.patch.object(self.fetcher.model_caches['chestnut'], 'get',
                           return_value=({**NATIVE, ModelFetcher.INDEX_KEY: False}, False)), \
         mock.patch.object(self.fetcher, '_fetch_and_cache_models', return_value=None) as fetch:
      for _ in range(3):
        self.fetcher.get_bundles_for_source('chestnut')
      fetch.assert_called_once_with('chestnut')

  def test_offline_native_chestnut_never_uses_index_only_artifacts(self):
    self.fetcher._fetch_and_cache_models('chestnut')
    cached = self.params.get(KEYS.catalog)
    choice = parsed(cached)[0].to_dict()
    choice['status'] = 'downloaded'
    self.params.put(KEYS.big_model, choice, block=True)
    with mock.patch.object(jetlink_adapter, 'lists_big_models', return_value=False), \
         mock.patch.object(self.fetcher, '_fetch_and_cache_models', return_value=None) as fetch:
      for _ in range(3):
        self.assertEqual(self.fetcher.get_bundles_for_source('chestnut'), [])
        self.validate({'bundles': []})
      fetch.assert_called_once_with('chestnut')
    self.assertEqual(self.params.get(KEYS.big_model), choice)
    self.assertIsNone(helpers.get_active_bundle(self.params, chestnut=True))
    self.assertEqual(self.params.get(KEYS.catalog), cached)

  def test_matching_cached_index_does_not_refetch(self):
    self.fetcher._fetch_and_cache_models('chestnut')
    self.refresh.reset_mock()
    self.assertEqual([b.ref for b in self.fetcher.get_bundles_for_source('chestnut')], [V2, V3])
    self.refresh.assert_not_called()


class TestModelChoices(IndexTest):
  def test_v2_choice_and_small_slot_survive_the_new_artifact_free_list(self):
    raw = selected()
    small = selected('1' * 40, 'Pop V2')
    self.params.put(KEYS.big_model, raw, block=True)
    self.params.put('ModelManager_ActiveBundle', small, block=True)
    before = os.stat(self.params.get_param_path(KEYS.big_model)).st_mtime_ns
    self.validate(self.catalog())
    self.validate(self.catalog())
    self.assertEqual(self.params.get(KEYS.big_model), raw)
    self.assertEqual(os.stat(self.params.get_param_path(KEYS.big_model)).st_mtime_ns, before)
    self.assertEqual(self.params.get('ModelManager_ActiveBundle'), small)

  def test_old_export_ref_remaps_to_the_same_onnx_instead_of_defaulting(self):
    self.params.put(KEYS.big_model, selected(OLD_V3, 'Cinque Terre V3'), block=True)
    self.validate(self.catalog())
    raw = self.params.get(KEYS.big_model)
    self.assertEqual(raw['ref'], V3)
    self.assertEqual(raw['displayName'], 'Cinque Terre V3')
    self.assertEqual(raw['models'], [])
    self.assertEqual(raw['status'], 'downloaded')

  def test_queued_old_ref_resolves_to_the_same_big_model(self):
    result = resolve_bundle_by_ref(OLD_V3, {'qcom': parsed(SMALL), 'chestnut': parsed(self.catalog())})
    self.assertIsNotNone(result)
    self.assertEqual((result[0].ref, result[1]), (V3, 'chestnut'))

  def test_native_chestnut_does_not_remap_an_old_ref_through_jetlink(self):
    with mock.patch.object(jetlink_adapter, 'lists_big_models', return_value=False), \
         mock.patch.object(jetlink_adapter, 'listed_ref') as remap:
      self.assertIsNone(resolve_bundle_by_ref(OLD_V3, {'chestnut': parsed(NATIVE)}))
    remap.assert_not_called()

  def test_empty_failed_catalog_keeps_the_choice(self):
    raw = selected()
    self.params.put(KEYS.big_model, raw, block=True)
    self.validate({'bundles': []})
    self.assertEqual(self.params.get(KEYS.big_model), raw)

  def test_no_choice_does_not_become_a_new_default_selection(self):
    self.validate(self.catalog())
    self.assertIsNone(self.params.get(KEYS.big_model))

  def test_native_chestnut_recovers_artifact_manifest_for_the_same_choice(self):
    indexed = parsed(self.catalog())[0].to_dict()
    indexed['status'] = 'downloaded'
    self.params.put(KEYS.big_model, indexed, block=True)
    self.validate(self.catalog())
    with mock.patch.object(jetlink_adapter, 'lists_big_models', return_value=False):
      self.validate(NATIVE)
    raw = self.params.get(KEYS.big_model)
    self.assertEqual(raw['ref'], V2)
    self.assertTrue(raw['models'])
    self.assertEqual(raw['status'], 'downloaded')

  def test_native_files_are_queued_after_offline_index_only_choice_gets_a_manifest(self):
    indexed = parsed(self.catalog())[0].to_dict()
    indexed['status'] = 'downloaded'
    self.params.put(KEYS.big_model, indexed, block=True)
    manager = manager_module.ModelManagerSP.__new__(manager_module.ModelManagerSP)
    manager.params = self.params
    manager.chestnut_present = True
    manager._big_files_checked = set()
    manager._fetch_big_model_files()
    self.assertEqual(manager._big_files_checked, set())
    self.assertIsNone(self.params.get('ModelManager_DownloadRef'))
    with mock.patch.object(jetlink_adapter, 'lists_big_models', return_value=False):
      self.validate(NATIVE)
    with mock.patch.object(manager_module, '_bundle_is_valid_locally', return_value=False):
      manager._fetch_big_model_files()
    # The manager queues this through Params.put's nonblocking worker.
    deadline = time.monotonic() + 2.0
    while self.params.get('ModelManager_DownloadRef') != V2 and time.monotonic() < deadline:
      time.sleep(0.005)
    self.assertEqual(self.params.get('ModelManager_DownloadRef'), V2)

  def test_catalog_refresh_remaps_even_after_this_process_validated_the_choice(self):
    self.index_data['models'][1]['ref'] = OLD_V3
    self.index_data['refs'][V3] = {'oid': V3_OID, 'size': 766354845}
    self.params.put(KEYS.big_model, selected(OLD_V3, 'Cinque Terre V3'), block=True)
    self.validate(self.catalog())
    self.index_data = copy.deepcopy(INDEX)
    self.validate(self.catalog())
    self.assertEqual(self.params.get(KEYS.big_model)['ref'], V3)

  def test_an_invalid_ref_does_not_crash_the_manager(self):
    raw = selected()
    raw['ref'] = ['invalid']
    self.params.put(KEYS.big_model, raw, block=True)
    self.validate(self.catalog())
    self.assertIsNone(self.params.get(KEYS.big_model))


if __name__ == '__main__':
  unittest.main()
