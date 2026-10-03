# Device log analysis: September 2026

Update: [JetLink v0.4.0 was installed on September 26](JETSON_UPDATE_2026-09-26.md). It supports the Jetson's existing JetPack 7.2.1 platform; the older platform-reversion guidance below is historical.

For the newer September 26 comma capture and drive analysis, see [Comma log analysis](COMMA_LOG_ANALYSIS_2026-09-26.md). Jetson platform and service findings below describe the earlier capture, not a current powered-off device check.

This report summarizes private captures collected from the comma 4 and Jetson Orin Nano Super on September 25, 2026. Raw routes, journals, archives, addresses, and hardware identifiers are deliberately excluded from Git.

The devices were physically disconnected during the September 25 snapshot. A missing USB gadget, an inactive JetLink server, and absent live JetLink parameters in that snapshot are therefore expected. They are not evidence of a drive-time failure.

## Historical JetLink captures

The useful Jetson captures contain successful TensorRT 10.3 engine loads and sustained USB inference sessions. A filtered session with warning samples from frames 231 through 30,929 covers roughly 25.6 minutes at 20 Hz.

| Metric in warning samples | Mean | p95 | Maximum |
| --- | ---: | ---: | ---: |
| GPU inference | 20.32 ms | 20.40 ms | 20.50 ms |
| Server total | 22.09 ms | 22.10 ms | 22.20 ms |
| USB send | 11.68 ms | 15.30 ms | 23.50 ms |

The larger mixed journal contains 336 slow-frame warnings. Across those warning lines, GPU inference averages 21.14 ms and server total averages 22.90 ms. USB send time is usually below 18 ms, with one 69.7 ms outlier. These are server-side warning samples rather than a distribution over every frame, so they must not be interpreted as whole-drive percentiles.

The historical journal also shows 125 USB connections, 124 disconnects, and 124 USB I/O errors across mixed runs, including short bursts of repeated connect followed by LIBUSB_ERROR_IO after a disconnect. The pinned JetLink server catches link errors and reopens the transport, but the old capture shows that retries could happen rapidly while the USB gadget remained enumerated. This is evidence to inspect the cable, power, and reconnect behavior on the next paired test; it does not identify a single cause by itself.

There are no matching comma route logs from September 20-21 in the current retained route set. Client-side end-to-end latency, fallback events, and frame loss therefore cannot be proved from these captures alone. The next diagnostic run should collect both sides under one label before route cleanup.

## Current platform findings

The Jetson currently reports L4T r39.2.1 and TensorRT 10.16.2. This repository documents and pins a JetPack 6.1 / L4T r36.4 / TensorRT 10.3 setup. Cached TensorRT plans are tied to the software and GPU environment; reconcile the Jetson image with the documented stack, then rebuild the engine before another drive.

The Jetson's current boot log also reports GPU ACR firmware/bootstrap failures and nvpmodel.service is failed, even though a direct query reports 25 W mode. Resolve those failures while parked before enabling JetLink. The network DHCP service failures are separate from the recorded inference timing.

The comma journal is dominated by a malformed /etc/udev/rules.d/comma-polkit.rules file containing polkit JavaScript in the udev rules directory. Move a validated rule to the proper polkit rules directory or remove the invalid file from the build. This is log noise and configuration debt; the available evidence does not connect it to JetLink latency.

Some early Jetson records begin in 1969 before wall-clock synchronization. Use monotonic timestamps or establish time before capture so cross-device events can be correlated reliably.

## Storage snapshot

The comma /data volume is 89% full with about 9.5 GB available. Its main consumers are:

| Path | Approximate size | Guidance |
| --- | ---: | --- |
| /data/media/0/realdata | 68 GB | Delete old routes only after preserving the paired logs needed for analysis. |
| /data/safe_staging | 2-4 GB | Remove only after confirming no update is active and the staging tree is obsolete. |
| /data/openpilot-before-745sp-20260922 | 703 MB | Remove if rollback to this backup is no longer needed. |
| /data/log | 477 MB | Archive any needed diagnostics, then prune old logs. |
| /data/scons_cache | 451 MB | Rebuildable; safe to clear while openpilot is stopped. |
| /data/media/0/models | 731 MB | Keep models that are selected or expensive to re-download. |

The root filesystem is separately 90% full. A same-filesystem scan accounts for essentially all used root space under the 3.6 GB /usr system image. Deleting routes from /data will not change the root filesystem percentage.

Prefer the device UI for route deletion. If using SSH, first list and copy the exact route directories required for analysis, stop openpilot if clearing active caches, and delete an explicit reviewed list. Avoid wildcard or broad recursive removal against /data/media/0/realdata.

## Next paired validation

1. Restore a supported Jetson software stack and verify the GPU and nvpmodel services.
2. Rebuild the TensorRT engine; do not reuse the TensorRT 10.3 plan after a platform change.
3. Connect the devices while parked and confirm SuperSpeed enumeration, engine readiness, and native-model fallback.
4. Capture the Jetson service journal and matching comma qlogs/rlogs for the same short route.
5. Run python tools/analyze_jetlink_log.py <jetlink-log> for a reproducible server-side timing summary, then inspect the paired comma log for end-to-end latency and fallback events.
