# Comma log analysis: September 26, 2026

Subsequent maintenance: [Jetson update to JetLink v0.4.0](JETSON_UPDATE_2026-09-26.md). The drive measurements below precede that update.

## Scope and evidence

Collected over SSH at approximately 20:58 UTC (13:58 PDT), with the car off and the Jetson unpowered as reported by the owner. The comma was offroad, JetlinkEnabled was 1, and there were no failed systemd units. No live Jetson connection or deployment was attempted. Missing Jetson USB enumeration in this snapshot is expected and is not a drive-time failure.

Downloaded 65 qlogs from the latest two completed routes (29 and 36 segments), plus 162 recent application log files. Private archives and analysis output remain under ignored `diagnostics/2026-09-26-offroad/`; raw routes, addresses, and device identifiers are not committed.

Both routes identify deployed commit `d57c4b533558bb2314f542a2ea78c3271b265eda`, on the device deployment branch, from the device's `ryanafdahl/openpilot` origin. This differs from this checkout's starting commit `66243ad71814fe296524587bd43d046561748ac0` in `ryanafdahl/Clarity-Pilot`. These measurements validate the observed deployment, not the current checkout or a new release.

## Latest two drives

The compact `drivingModelData` messages carry the model mode, execution time, and frame-drop field; these qlogs contain no `modelV2` messages. The analyzer converts execution seconds to milliseconds and reports nearest-rank p95. Durations below are per-route recorded spans, excluding the gap between routes.

| Measurement | Earlier route | Latest route |
| --- | ---: | ---: |
| Recorded span | 28.91 min | 35.91 min |
| Large-model samples | 3,387 | 4,222 |
| Small-model samples before joining | 62 | 68 |
| First large-model sample, seconds from route start | 41.52 | 43.66 |
| Large-model execution mean | 38.68 ms | 38.43 ms |
| Large-model execution p95 | 40.66 ms | 40.26 ms |
| Large-model execution maximum | 47.99 ms | 47.69 ms |
| Reported frame-drop percentage, maximum sampled | 0% | 0% |

Each route has one sampled transition from small to large and no sampled transition back. Application logs also show successful joins at 19:37:52 and 20:09:06 UTC without a subsequent fallback before each route ended. This supports sustained large-model operation in these drives. Qlogs sample model messages at approximately 2 Hz; zero sampled frame drops and sub-50 ms sampled execution times do not prove every inference met its deadline, nor measure complete camera-to-control latency.

Small-model execution has roughly 1.29-second maxima before the large-model join, despite p95 values of 27.01 and 26.76 ms. Startup communication warnings occur approximately 9-12 seconds into each route, before the JetLink joins. Investigate initialization/warmup separately from steady-state large-model timing; do not remove timeout or fallback protections based on these sampled results.

The latest route also has one sampled `fcw` event at +111.17 seconds, one `steerSaturated` at +256.31 seconds, and one `selfdrivedLagging` at +494.06 seconds. These are event-message counts, not independent incident counts or proof of a JetLink cause. Full-rate logs and surrounding driving context are needed to assess them.

## Earlier transport failure and recovery

The wider application-log window contains a fallback at 17:15:19.605 UTC. Its traceback ends in `jetlink.transport.base.LinkError: send timed out; link abandoned`, raised while sending an inference request through FunctionFS. The client logged a five-second retry and rejoined the large model at approximately 17:15:26 UTC.

Nearby warning samples show 269.5 ms send time on the initial join and 165.3 ms on a retry frame, while server GPU time is about 23.4 ms and total server time about 25-27 ms. This points to a transport-side stall in that episode, rather than a demonstrated GPU inference slowdown. The capture does not establish whether USB scheduling, cable/power, host memory pressure, or another cause produced the stall. The latest two routes do not reproduce that fallback.

## Telemetry and other findings

Across 3,578 JetLink telemetry records after 19:36:40 UTC in the captured application logs:

- GPU temperature: 52.4-64.1 C, mean 61.68 C.
- Reported power: 9.09-13.60 W, mean 12.76 W; configured limit reported as 25 W.
- GPU clock: 918 MHz in every sample.
- Reported supply: 4.912-4.960 V.

These are comma-recorded historical Jetson telemetry, not a fresh Jetson health check. They do not show a clock reduction in this window and do not prove the cause or absence of transient power issues.

The broader application-log window contains 708 model-catalog request DNS failures and 708 corresponding expired-cache fallback messages. The two catalog URLs each failed 354 times. This is a separate network/catalog-refresh issue; cached models remained usable. Prime/firehose requests also encountered DNS failures.

Storage at collection: `/data` 90% used with about 8.9 GB available; root 90% used with about 442 MB available. No files were removed. Preserve needed route evidence before cleanup. The previous report's Jetson platform/service observations are historical and were not rechecked with the Jetson powered off.

## Repository update and validation

Added `tools/analyze_comma_routes.py` for repeatable, per-route summaries from local qlogs. It suppresses route IDs and GPS data from normal output, counts event messages, records sampled mode transitions, and returns failure on parse errors or missing model samples. Run in an openpilot Python environment, using extracted archive paths or device-local paths:

```sh
PYTHONPATH=/data/openpilot /usr/local/venv/bin/python tools/analyze_comma_routes.py '/path/to/extracted/*/qlog.zst'
```

Validation: all 65 device qlogs parsed with no errors; 7,739 compact model samples were summarized. Ruff passed with the device's openpilot configuration, and the no-matching-files case returned argparse exit status 2. No runtime driving code, model choice, device settings, or safety thresholds were changed.

Next useful check is a parked paired capture of both devices around initial join/rejoin, with full-rate rlogs around the earlier send timeout or any repeat of it. Also inspect startup warmup and the isolated selfdrived lag event before attributing them to JetLink. A powered-off snapshot cannot establish the Jetson's present service or GPU status.

## Follow-up: startup and isolated lag investigation

The earlier full-rate capture completed: five rlogs cover segment 0 of both routes and segments 7–9 of the latest route. All five were decoded locally without a truncated segment. This evidence was collected before the v0.4.0 update and is separate from the incomplete archive of the subsequent short drive.

Both routes' slowest startup inference was the first small-model frame: 1,287.87 and 1,288.84 ms, at +10.54 and +9.67 seconds respectively. These precede the large-model joins and coincide with startup communication warnings. The full-rate first large-model frames took 66.62 and 58.82 ms at +41.35 and +43.43 seconds; the compact qlogs missed those first frames. This reinforces the sampling limitation of the original table. The startup delay is real, but the logs alone do not separate model initialization, compilation, camera readiness, and scheduling costs within it.

The isolated `selfdrivedLagging` event is at +494.063 seconds. In the surrounding ten seconds, all 200 full-rate model messages use the large model, with mean execution 38.35 ms, maximum 48.05 ms, and reported frame-drop field zero. Selfdrive-state publication intervals briefly rise to about 24 ms and then 34.95 ms immediately before the event. The nearest state has `enabled=false`; this field alone does not establish the state of every custom assistance feature.

This supports a delayed comma selfdrive loop, without evidence of a concurrent Jetson inference slowdown or model fallback. The loop's ratekeeper triggers `selfdrivedLagging` independently of the model's execution-time field. Device telemetry in that ten-second window reports thermal state `ok` and memory usage 89%; CPU samples are not enough to identify the scheduling or blocking cause. No safety threshold was changed to hide the event.

The [post-update report](JETLINK_DRIVE_2026-09-26.md) documents the new short drive, explains the repeated offroad catalog DNS retries, and records the separate Jetson startup ordering repair. The original one-off lag's underlying scheduling cause and the initial USB exchange delay remain unproven; neither is established as a sustained GPU performance problem.
