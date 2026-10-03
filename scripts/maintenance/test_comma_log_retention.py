import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('retention', Path(__file__).with_name('comma_log_retention.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class RetentionTests(unittest.TestCase):
  def setUp(self):
    self.tmp = tempfile.TemporaryDirectory()
    self.addCleanup(self.tmp.cleanup)
    self.root = Path(self.tmp.name)
    self.paths = []
    for i in range(5):
      p = self.root / f'{i:08d}--abcdef--0'
      p.mkdir()
      (p / 'rlog').write_bytes(b'x' * 10)
      os.utime(p, (100 + i, 100 + i))
      self.paths.append(p)

  def run_cleanup(self, **kwargs):
    with patch.object(m, 'marked', side_effect=lambda p: p.name.startswith('00000001')):
      return m.cleanup(self.root, kwargs.pop('offroad', lambda: True), budget=0, reserve=0,
                       free_bytes=lambda: 1000, **kwargs)

  def test_dry_run_preserves_files(self):
    self.assertEqual(self.run_cleanup()['segments_removed_or_planned'], 2)
    self.assertTrue(all(p.exists() for p in self.paths))

  def test_protects_recent_marked_locked_and_unrelated(self):
    (self.paths[0] / 'rlog.lock').touch()
    (self.root / 'models').mkdir()
    self.run_cleanup(apply=True)
    self.assertFalse(self.paths[2].exists())
    self.assertTrue(all(self.paths[i].exists() for i in [0, 1, 3, 4]))
    self.assertTrue((self.root / 'models').exists())

  def test_ignition_change_stops_deletion(self):
    states = iter([True, False])
    self.run_cleanup(apply=True, offroad=lambda: next(states))
    self.assertTrue(all(p.exists() for p in self.paths))

  def test_onroad_is_noop(self):
    self.assertEqual(self.run_cleanup(apply=True, offroad=lambda: False), {'skipped': 'not offroad'})

  def test_hexadecimal_routes_are_included_and_ordered(self):
    for route in ['0000000f', '00000010']:
      p = self.root / (route + '--abcdef--0')
      p.mkdir()
      (p / 'rlog').write_bytes(b'x' * 10)
    self.run_cleanup(apply=True)
    self.assertFalse(self.paths[4].exists())
    self.assertTrue((self.root / '0000000f--abcdef--0').exists())
    self.assertTrue((self.root / '00000010--abcdef--0').exists())

  @unittest.skipUnless(os.name == 'posix', 'symlink test requires POSIX')
  def test_symlink_cannot_delete_external_data(self):
    with tempfile.TemporaryDirectory() as outside:
      target = Path(outside) / 'keep'
      target.write_text('keep')
      (self.root / '00000099--abcdef--0').symlink_to(outside, target_is_directory=True)
      self.run_cleanup(apply=True)
      self.assertTrue(target.exists())


if __name__ == '__main__':
  unittest.main()
