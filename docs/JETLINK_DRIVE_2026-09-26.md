# JetLink v0.4.0 drive and startup investigation — September 26, 2026

The short drive confirms large-model operation after the [v0.4.0 update](JETSON_UPDATE_2026-09-26.md). A subsequent desk boot exposed a separate power-initialization ordering failure, which was corrected and passed one reboot check. The owner saw the green indicator while parked and believes it stayed active during the drive.

## Evidence and limits

The comma completed a summary of all four qlogs before its Wi-Fi connection dropped: 229.76 seconds recorded, 438 compact model samples, no parse errors. Only the first two qlog segments transferred completely; the route archive is incomplete, and no full-rate rlogs from this new drive arrived. Fifteen application logs transferred successfully. The comma remains on deployed commit `d57c4b533558bb2314f542a2ea78c3271b265eda`; no comma software was changed.

Jetson service state, kernel logs, and syslog were collected at the desk. Syslog retains the car boot and USB inference records even though the corresponding service-journal queries returned no entries. The Jetson car-boot clock was unset (1970 timestamps), so its records cannot be aligned to comma UTC by their wall-clock timestamps. Private evidence is under ignored `diagnostics/2026-09-26-v040-drive/` and the Jetson user's `jetlink-drive-20260926-v040/` directory.

## Drive results

| Measurement | Result |
| --- | ---: |
| Recorded route span | 3 min 49.76 s |
| First small-model sample | +10.50 s |
| First large-model sample | +40.67 s |
| Return to small model | +227.76 s |
| Sampled large-model interval | 187.09 s |
| Large-model samples | 374 |
| Large-model execution mean / p95 | 31.70 / 33.79 ms |
| Large-model maximum | 204.81 ms, first large-model sample |
| Reported frame-drop field, mean / maximum | 0.078% / 1.407% |

The earlier two drives averaged 38.43–38.68 ms: the new mean is about 18% lower. These are different drives, and both the runtime and power mode changed, so this is an observation rather than an isolated release benchmark. Qlogs sample model messages at about 2 Hz. The frame-drop field is a smoothed reported value, not an exact aggregate count of missed frames; execution time is not complete camera-to-control latency.

At the join, the comma recorded a 162.9 ms request send, 23.6 ms reply wait, and 17.8 ms server GPU time. All eight `modeldLagging` event messages occur between +40.72 and +43.70 seconds. Startup communication warnings also occur around +9.55–11.56 seconds. The first small-model sample takes 1,303.10 ms. These distinguish small-model startup and the initial USB exchange from steady inference. The new route has no `selfdrivedLagging` event.

The recovered Jetson car-boot records show an engine ready about 39 seconds after its unset clock began, followed by inference. Across 38 server `slow frame` warnings, GPU time was 17.6–19.1 ms and server total time 18.4–20.1 ms; sending the result took 10.0–13.2 ms. Those are warning-selected samples, not overall timing statistics. They do not show a sustained GPU slowdown.

At 21:30:42 UTC, the comma fell back with `host dropped the gadget configuration`. Modeld received its stop signal at 21:30:44 UTC, approximately two seconds later. The timing is consistent with the end of the drive and switched power, but does not establish ignition-off as the cause. Full-rate shutdown context is still missing; the final disconnect should not be presented as either a proven in-motion failure or a proven normal shutdown.

Across 179 comma-recorded Jetson telemetry samples, GPU temperature was 54.3–64.2 C, power 8.93–12.95 W, supply 4.920–4.960 V, and GPU clock 1,020 MHz throughout. No clock reduction appears in those samples. Telemetry still reports a 25 W limit field; that field alone does not identify the selected nvpmodel profile. MAXN_SUPER mode 2 was separately verified on the Jetson.

## Repeated DNS failures

There are 160 explicit name-resolution failures from 21:30:44.491 through 21:32:06.989 UTC, followed by one HTTP read timeout at 21:32:28.702. All 161 fetch failures have corresponding expired-cache fallback messages. They begin as the comma transitions offroad, after large-model inference ends.

The repository's [process configuration](../openpilot/system/manager/process_config.py) runs the catalog manager only offroad. Its [main loop](../openpilot/sunnypilot/models/manager.py) fetches both sources at 1 Hz; the [fetcher](../openpilot/sunnypilot/models/fetcher.py) falls back to expired cached data on transport failure without imposing a retry delay. Once the cache expires, a fast DNS failure therefore produces about two failed requests per second. This explains the repeated log entries and why cached models remain usable. The deployed logs match this behavior, although the deployed commit differs from this checkout.

The capture establishes resolver/network unavailability at the time, but cannot distinguish Wi-Fi loss, router/upstream DNS trouble, or another connectivity failure. Do not replace the system resolver based on this evidence. A per-source bounded retry backoff would address the repeated requests; it has not been implemented or deployed in this maintenance pass.

## Jetson boot failure and applied fix

On returning to the desk, `jetlink-server.service` was inactive because its required `nvpmodel.service` had failed with exit status 234. CDI generation had run before nvpmodel. Reapplying nvpmodel reported an already-created GPU golden-image context and requested a reboot. Merely querying the saved power profile still returned MAXN_SUPER, so that query alone was insufficient to prove successful power initialization.

This fits a GPU initialization ordering race: CDI touches the GPU before nvpmodel can apply its power-gating configuration. NVIDIA's [power-management documentation](https://docs.nvidia.com/jetson/archives/r39.2/DeveloperGuide/SD/PlatformPowerAndPerformance/JetsonOrinNanoSeriesJetsonOrinNxSeriesAndJetsonAgxOrinSeries.html) describes the restrictions on changing initialized GPU power state. A [first-hand R39.2 report on NVIDIA's forum](https://forums.developer.nvidia.com/t/jetson-r39-2-package-ships-stale-nvidia-cdi-refresh-service/377209) describes the same CDI/nvpmodel ordering and status 234. The local before/after evidence supports this diagnosis; a single successful reboot does not measure the failure rate.

Installed the tracked [CDI drop-in](../scripts/jetson/nvidia-cdi-refresh.service.d/20-after-nvpmodel.conf) at `/etc/systemd/system/nvidia-cdi-refresh.service.d/20-after-nvpmodel.conf`:

```ini
[Unit]
# Apply Jetson GPU power-gating state before CDI initializes the GPU.
Requires=nvpmodel.service
After=nvpmodel.service
```

This device already has `nvpmodel.service` configured with `Type=oneshot` and `RemainAfterExit=yes`, so requiring it later does not rerun successful power initialization. **Check that prerequisite before reusing this drop-in on another installation.** Stock units with `RemainAfterExit=no` need a boot-scoped readiness gate instead. The existing JetLink dependency on successful nvpmodel was retained.

The original units and new drop-in were backed up. After installation, `systemctl daemon-reload` and `systemd-analyze verify nvpmodel.service nvidia-cdi-refresh.service jetlink-server.service` succeeded. Verification printed two unrelated existing warnings about obsolete syslog output settings.

One software reboot then produced this order, using monotonic timestamps:

| Milestone | Seconds after boot |
| --- | ---: |
| nvpmodel command starts / succeeds | 11.916 / 12.213 |
| CDI command starts / succeeds | 12.250 / 12.957 |
| JetLink service starts | 17.212 |
| Engine ready after CUDA graph capture | 20.609 |

Final checks: nvpmodel active/exited successfully; CDI completed successfully (inactive afterward is normal for its oneshot unit); JetLink active/running with `NRestarts=0`; MAXN_SUPER mode 2 and 1,020 MHz GPU clock. The service remains running at the desk, waiting for the comma USB gadget. TensorRT still emits a plan/device compatibility warning before successfully loading the locally rebuilt engine; this warning was not eliminated.

Rollback consists of removing only this added drop-in, reloading systemd, and rebooting; it restores the previous ordering and may restore the failure. Preserve the backup. No timeout, fallback, or driving safety thresholds were relaxed.

## Remaining validation

The drive preceded the boot-order fix. One software reboot passed afterward; a fresh car power cycle and parked USB join have not yet been tested with that fix. The complete new-drive rlogs and missing qlog segments can be collected when the owner next powers the comma. No additional comma access is needed to preserve the current findings.

The [earlier route report](COMMA_LOG_ANALYSIS_2026-09-26.md#follow-up-startup-and-isolated-lag-investigation) also now includes full-rate investigation of the original isolated lag event. The repository records diagnostic findings and the applied device configuration; it does not claim that the initial USB send stall or catalog retry behavior has been fixed.
