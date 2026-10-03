#!/usr/bin/env python3
"""Offroad-only recording retention. Dry-run unless --apply is supplied."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil

GIB = 1024 ** 3
SEGMENT = re.compile(r'^(?:[0-9a-f]{8}--[0-9a-f]+|\d{4}-\d{2}-\d{2}--\d{2}-\d{2}-\d{2})--\d+$')


def size(path):
  total = 0
  for p in path.rglob('*'):
    try:
      if p.is_file() and not p.is_symlink():
        total += p.stat().st_size
    except FileNotFoundError:
      pass  # The native deleter may have removed a file concurrently.
  return total


def creation_order(path):
  route, segment = path.name.rsplit('--', 1)
  # Route counters are monotonic. Directory mtimes change when files are uploaded
  # or locked, so cannot identify the latest routes. Legacy dated routes came first.
  return (bool(re.match(r'^[0-9a-f]{8}--', route)), route, int(segment))


def marked(path):
  try:
    return os.getxattr(path, 'user.preserve') == b'1'
  except OSError:
    return False


def cleanup(root, offroad, *, apply=False, budget=20 * GIB, reserve=20 * GIB, free_bytes=None):
  root = root.resolve(strict=True)
  free_bytes = free_bytes or (lambda: shutil.disk_usage(root).free)
  if not offroad():
    return {'skipped': 'not offroad'}
  segments = sorted((p for p in root.iterdir() if SEGMENT.fullmatch(p.name) and
                     p.is_dir() and not p.is_symlink()), key=creation_order)
  sizes = {p: size(p) for p in segments}
  routes = list(dict.fromkeys(p.name.rsplit('--', 1)[0] for p in reversed(segments)))
  protected_routes = set(routes[:2])
  protected = set()
  for p in [p for p in reversed(segments) if marked(p)]:
    route, number = p.name.rsplit('--', 1)
    protected.update(f'{route}--{i}' for i in range(max(0, int(number) - 2), int(number) + 1))
  total = sum(sizes.values())
  before, deleted, removed, free_before = total, 0, 0, free_bytes()
  for p in segments:
    free = free_bytes() if apply else free_before + removed
    if total <= budget and free >= reserve:
      break
    if p.name.rsplit('--', 1)[0] in protected_routes or p.name in protected:
      continue
    # Recheck immediately before deletion: never traverse a replaced symlink,
    # delete outside this exact root, or delete a recording still being written.
    if not offroad():
      break
    if p.is_symlink() or not p.exists() or p.resolve().parent != root:
      continue
    if any(p.rglob('*.lock')) or marked(p):
      continue
    try:
      if apply:
        shutil.rmtree(p)
    except OSError:
      continue
    deleted += 1
    removed += sizes[p]
    total -= sizes[p]
  return {'apply': apply, 'segments_removed_or_planned': deleted, 'bytes_before': before,
          'bytes_after_or_planned': total, 'bytes_removed_or_planned': removed,
          'free_bytes': free_bytes(), 'budget_bytes': budget, 'reserve_bytes': reserve,
          'protected_routes': len(protected_routes), 'target_met': total <= budget and
          (free_bytes() if apply else free_before + removed) >= reserve}


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--apply', action='store_true')
  args = parser.parse_args()
  def offroad():
    try:
      return Path('/data/params/d/IsOffroad').read_bytes().strip() == b'1'
    except OSError:
      return False
  print(json.dumps(cleanup(Path('/data/media/0/realdata'), offroad, apply=args.apply)))


if __name__ == '__main__':
  main()
