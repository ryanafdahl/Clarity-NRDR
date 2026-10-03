#!/usr/bin/env python3
"""Summarize JetLink server timing and connection events from a text log."""

from __future__ import annotations

import argparse
import re
import statistics
from pathlib import Path


SLOW_FRAME_RE = re.compile(
  r"slow frame (?P<frame>\d+): gpu (?P<gpu>[\d.]+) queue (?P<queue>[\d.]+) "
  r"total (?P<total>[\d.]+) send (?P<send>[\d.]+) ms"
)


def percentile(values: list[float], fraction: float) -> float:
  """Return a nearest-rank percentile for a compact field report."""
  ordered = sorted(values)
  index = max(0, min(len(ordered) - 1, round(fraction * (len(ordered) - 1))))
  return ordered[index]


def metric_line(name: str, values: list[float]) -> str:
  return (
    f"{name:>5}: mean={statistics.fmean(values):5.2f} ms  "
    f"p95={percentile(values, 0.95):5.2f} ms  max={max(values):5.2f} ms"
  )


def main() -> int:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("log", type=Path)
  args = parser.parse_args()

  text = args.log.read_text(encoding="utf-8", errors="replace")
  samples = [match.groupdict() for match in SLOW_FRAME_RE.finditer(text)]
  connects = text.count("client connected over usb")
  disconnects = text.count("client disconnected")
  usb_errors = len(re.findall(r"usb bulk (?:read|write) failed", text))

  print(f"file: {args.log}")
  print(f"slow-frame samples: {len(samples)}")
  print(f"connections: {connects}; disconnects: {disconnects}; USB I/O errors: {usb_errors}")
  if not samples:
    return 0

  frames = [int(sample["frame"]) for sample in samples]
  print(f"observed frame range: {min(frames)}..{max(frames)}")
  for metric in ("gpu", "queue", "total", "send"):
    print(metric_line(metric, [float(sample[metric]) for sample in samples]))
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
