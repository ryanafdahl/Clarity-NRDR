#!/usr/bin/env python3
"""Summarize local comma qlogs; output excludes route IDs and GPS data.

Run with openpilot's Python environment and a quoted glob of qlog paths.
Timing and mode transitions describe sampled drivingModelData, not every frame.
"""
import argparse
import glob
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from openpilot.tools.lib.logreader import LogReader


def stats(values):
  values = sorted(values)
  return {"samples": len(values), "mean": statistics.fmean(values),
          "p95": values[math.ceil(len(values) * .95) - 1], "max": values[-1]}


def summarize(files):
  metrics = defaultdict(list)
  modes, events = Counter(), Counter()
  transitions, notable, errors, commits = [], [], [], set()
  first = last = previous = None
  for path in sorted(files, key=lambda p: int(p.parent.name.rsplit("--", 1)[1])):
    try:
      for e in LogReader(str(path), sort_by_time=True):
        t, kind = e.logMonoTime / 1e9, e.which()
        first = t if first is None else min(first, t)
        last = t if last is None else max(last, t)
        if kind == "initData":
          commits.add(e.initData.gitCommit)
        elif kind == "drivingModelData":
          model = e.drivingModelData
          mode = "large" if model.big else "small"
          modes[mode] += 1
          metrics[mode + "_execution_ms"].append(model.modelExecutionTime * 1000)
          metrics[mode + "_frame_drop_percent"].append(model.frameDropPerc)
          if mode != previous:
            transitions.append({"seconds": t - first, "mode": mode})
            previous = mode
        elif kind == "onroadEvents":
          for event in e.onroadEvents:
            name = str(event.name)
            events[name] += 1
            if name in ("commIssue", "commIssueAvgFreq", "selfdrivedLagging", "fcw", "steerSaturated"):
              notable.append({"seconds": t - first, "event": name})
    except Exception as exc:
      errors.append({"segment": path.parent.name.rsplit("--", 1)[1], "error": str(exc)})
  return {"segments": len(files), "span_seconds": None if first is None else last - first,
          "commits": sorted(commits), "model_samples": dict(modes),
          "metrics": {k: stats(v) for k, v in metrics.items()}, "sampled_mode_transitions": transitions,
          "event_message_counts": dict(events), "notable_event_samples": notable, "errors": errors}


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("paths", nargs="+", help="qlog paths or glob patterns")
  args = parser.parse_args()
  files = sorted({Path(p) for pattern in args.paths for p in glob.glob(pattern)})
  if not files:
    parser.error("No matching qlogs")
  routes = defaultdict(list)
  for path in files:
    routes[path.parent.name.rsplit("--", 1)[0]].append(path)
  result = [summarize(paths) for _, paths in sorted(routes.items())]
  print(json.dumps({"routes": result}, indent=2))
  return int(any(r["errors"] or not r["model_samples"] for r in result))


if __name__ == "__main__":
  raise SystemExit(main())
