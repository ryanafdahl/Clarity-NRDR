# Clarity-NRDR

Clarity-Pilot with explicitly selected NRDR-derived Honda Clarity TRW-A020 PTC
EPS support and JetLink 0.8.7. Stock and legacy 3x tuning remain available with
PTC off. The PTC confirmation is persistent and off by default on a new install.

Read [firmware selection and PTC behavior](docs/CLARITY_PTC.md) before enabling
it. The steering profile comes from [nrdr/openpilot, nrdr-clean](https://github.com/nrdr/openpilot/tree/nrdr-clean),
pinned to `b3366b5b56512805be8f0bf832b4981bfd958072`.

**This is an experimental build for one car. One recorded drive does not
qualify the firmware or physical steering response for general use.**

## Latest deployment and drive review

The [October 17 PTC drive review](docs/CLARITY_PTC_DRIVE_2026-10-17.md) confirms
the new profile was active on the comma 4 after the owner-reported firmware
flash. The 910.22-second recording contains **17,681 large-model outputs**, USB 3
Orin/TensorRT handshakes, no observed fallback after joining, and zero recorded
communication, lag or controls-mismatch events. Large-model execution averaged
**23.41 ms**, with **31.98 ms maximum**. Camera-to-publication p95 was **49.63 ms**;
these are different timing measurements.

The report also covers temporary EPS inhibition during driver steering input,
four stock collision-warning samples, low-speed tracking/re-entry limits, the
startup USB retry, and decoded zero-torque/LKAS-release checks. It is based on
25 full-rate and 25 compact logs across the preceding and PTC drives, with every
downloaded file verified by SHA-256. [Technical aggregates](docs/validation/clarity-ptc-drive-2026-10-17.json)
exclude raw routes, location and identifiers.

## Current configuration

| Component | Verified configuration |
| --- | --- |
| Repository and branch | `ryanafdahl/Clarity-NRDR`, `main` |
| Driving device | comma 4; build and UI verified on the device |
| PTC UI on comma 4 | Settings → vehicle → Clarity PTC; explicit firmware confirmation |
| PTC UI on comma 3X | Vehicle → Clarity PTC Firmware Installed (Honda) |
| Reviewed EPS image | ClarityMax 20260928 Pminus5/A280Flat/KFF45/Tracker3200/Norm1650-3840; see the exact filename and hash in the PTC guide |
| JetLink client | Stable 0.8.7, `d26001b`, protocol 3, adapter API 3 |
| Jetson server | Last checked live as native 0.8.7; October 17 drive identifies Orin-sm87 / TensorRT 10.16.2.10 |
| Jetson hardware | Orin Nano Super Developer Kit, 8 GB; module P3767-0005, carrier P3768-0000, tegra234 |
| Jetson OS and power | JetPack 7.2.1 / L4T 39.2.1, MAXN_SUPER; switched car power |
| Current saved small model | CD210, February 3, 2026; selection preserved |
| Current saved large model | Cinque Terre V2, September 8, 2026; selection preserved |
| Data connection | Jetson USB-A host → comma USB-C, USB 3 data cable; separate power |
| Jetson model cache | `/mnt/data/jetlink` |

The Jetson is powered off after parking; its current absence is not a connection
failure. Its independent boot journal and a new parked test were unavailable
for the latest review. Pixel results in the older reports describe earlier
software and do not qualify the current Android release.

## Firmware and profile selection

The owner reports flashing
`ClarityMax-20260928-Pminus5-A280Flat-KFF45-Tracker3200-Norm1650-3840.rwd` and enabling
PTC. The drive confirms the host's PTC flag, linear 3840 command map and matched
PID gains. The existing EPS query cannot cryptographically identify the flashed
calibration; the reviewed local file hash and the owner's flashing record are
separate evidence.

Keep PTC **off** for stock firmware and the older 3x torque mod. After installing
a reviewed PTC image, enable the UI setting while parked and restart the device.
Updates preserve an existing confirmation; do not clear or force it during an
update. [Supported files, activation gates and limitations](docs/CLARITY_PTC.md).

## How it works

The comma handles cameras, image warp, model parsing, vehicle controls, driver
monitoring and CAN. JetLink runs the large model on one attached accelerator.
The selected small model starts first; a ready large model joins when controls
permit the handoff. Link loss returns inference to the small model and invokes
the existing takeover protections. This does not guarantee uninterrupted
engagement. EPS profile selection is independent of accelerator selection.

The current source pins [JetLink v0.8.7](https://github.com/zoompilot/jetlink/releases/tag/v0.8.7).
Its resident USB owner, API 3 handoff checks, model preparation and camera warp
have been integrated and tested. On the comma choose **Settings → Models →
JetLink → USB** and select the large model. [Setup and validation](docs/JETLINK.md).

## Repository and installed-device updates

This repository is the source of record for Clarity-NRDR:

```sh
git clone --recurse-submodules --branch main https://github.com/ryanafdahl/Clarity-NRDR.git
cd Clarity-NRDR
```

The current comma was installed directly from this source checkout. A dedicated
Custom Software installer URL for Clarity-NRDR has not been validated. Preserve
settings, needed logs and rollback files before any reinstall. Publishing a
commit does not update an installed device automatically.

For an existing matching checkout, update while parked, review local changes,
build with the device's normal source-install workflow, then restart and check
its recorded profile and model selections:

```sh
git pull --ff-only
git submodule update --init --recursive
```

For the matching native Jetson installation, retain its power settings and
engine cache and use the pinned upstream update:

```sh
jetlink update --ref v0.8.7
jetlink status
```

Follow the [Jetson guide at v0.8.7](https://github.com/zoompilot/jetlink/blob/v0.8.7/docs/jetson.md)
for installation. [Current Android guide](https://github.com/zoompilot/jetlink/blob/v0.8.7/docs/android-app.md):
the archived 0.8.0 APK is historical and was not updated or qualified in this PTC review.

## Validation and retained history

The current [PTC regression workflow](.github/workflows/clarity-ptc.yml) covers
firmware gates, PID/geometry, Honda CAN and native safety behavior. The comma 4
menu was checked with 33 hidden-window UI tests and actual device rendering;
software tests and one recorded drive leave the physical qualifications listed
in the [latest report](docs/CLARITY_PTC_DRIVE_2026-10-17.md) open.

[Storage maintenance and rollback](scripts/maintenance/README.md) describe the
recording budget, protected recent routes and Jetson log retention. Keep raw
recordings private. Earlier measurements below retain their original dates and
deployments; they are not results for the PTC image.

## Historical drive measurements

The [October 3 full-rate analysis](docs/JETLINK_DRIVE_2026-10-03.md) covers a **331.80-second** recording on the updated Clarity Pilot deployment. The Jetson joined at **+28.21 s**, followed by **6,071 consecutive large-model outputs** with no recorded fallback or large-model frame-ID gap. Comma-reported model execution averaged **25.77 ms**, with **27.24 ms p95**. Its maximum, **52.36 ms**, was the join frame. These are model-run timings, not pure GPU or complete vehicle-control latency.

The first small-model output took **1.28 s** and was invalid; startup skipped 26 camera frame IDs. Both startup outliers preceded engagement. No lag or communication event was recorded. The comma retained 290 Jetson telemetry samples, but the drive's independent server journal could not be recovered after the Jetson was moved to the desk. Its desk boot loaded V2 at 11.26 s; that is not a measurement of the drive's boot time. See the report for the timeline, other warnings, and limits.

The same report records removal of the retired USB Wi-Fi dongle's `rtl8821au` DKMS driver. Ethernet and JetLink stayed active; a rollback archive was retained on the Jetson. The Pixel still requires its own inference and USB qualification.

The following results describe older builds:

The [September 26 short drive](docs/JETLINK_DRIVE_2026-09-26.md) recorded 3 minutes 50 seconds, including about 3 minutes on the large model. Sampled large-model execution averaged **31.70 ms**, with **33.79 ms p95**. The largest sample, **204.81 ms**, occurred at the initial large-model join. These are sampled inference timings, not complete camera-to-control latency or a guarantee that every frame met its deadline.

A later desk boot exposed a CDI/nvpmodel startup-order problem. The applied fix passed **one software reboot**, with the engine ready **20.61 seconds after boot**. The drive preceded that fix. A new car power-cycle test and complete full-rate logs for the short drive remain pending; the final USB disconnect occurred about two seconds before modeld stopped, and its precise cause is unconfirmed.

The drive used comma commit `d57c4b533558bb2314f542a2ea78c3271b265eda` from the separate deployment repository. These results describe that device configuration, not a road validation of every change on this repository's `main`.

For the next parked check, confirm the server and engine are ready, the comma shows a green accelerator indicator, and telemetry is live. `modelV2.big=true` in full-rate logs or `drivingModelData.big=true` in qlogs confirms large-model output. Keep logs from both devices when investigating a join, fallback, or disconnect; the icon alone cannot establish continuous operation.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| JetLink is inactive after boot | Inspect `jetlink status` and `jetlink-server.service` first. The CDI/nvpmodel notes below describe the older Docker installation; current 0.8.7 runs natively. |
| Accelerator never becomes ready | Check the USB-A-to-USB-C data cable, JetLink USB setting, server status, selected model, and engine-preparation log. |
| Delay or lag at startup | Separate small-model initialization, Jetson boot, engine loading, and the first USB inference exchange. Startup outliers do not establish steady-state GPU slowdown. |
| USB link drops | Compare both devices' logs with the timing of power changes; inspect the cable, USB negotiation, supply, and cooling. Preserve fallback protections. |
| Model preparation fails | Check runtime compatibility and available cache space. Avoid concurrent engine builds against the same cache. |
| Repeated catalog DNS warnings | Check offroad internet access. The catalog manager retries both sources every second when its cache is expired; cached models may remain usable. Retry backoff has not yet been added. |

The tracked [CDI dependency drop-in](scripts/jetson/nvidia-cdi-refresh.service.d/20-after-nvpmodel.conf) makes CDI wait for successful power initialization. It was applied to this Jetson, whose nvpmodel unit has `RemainAfterExit=yes`. **Do not copy it blindly onto a stock unit with `RemainAfterExit=no`.** The [boot-order investigation](docs/JETLINK_DRIVE_2026-09-26.md#jetson-boot-failure-and-applied-fix) explains the prerequisite, validation, and rollback.

For a bounded startup capture on the Jetson:

```sh
sudo journalctl -b -u nvpmodel.service -u nvidia-cdi-refresh.service -u jetlink-server.service -n 150 --no-pager
```

## Logs and reports

| Report | Covers |
| --- | --- |
| [October 17 PTC drive](docs/CLARITY_PTC_DRIVE_2026-10-17.md) | Active PTC profile, full-rate USB/model timing, decoded steering release, EPS status and remaining limits |
| [October 3 V2 drive and Wi-Fi retirement](docs/JETLINK_DRIVE_2026-10-03.md) | Full-rate frame timings, startup retry, telemetry, journal limits, and external USB Wi-Fi driver removal |
| [Comma drive analysis](docs/COMMA_LOG_ANALYSIS_2026-09-26.md) | Two earlier drives, first-frame delays, and the isolated selfdrive-loop lag investigation |
| [Jetson v0.4.0 update](docs/JETSON_UPDATE_2026-09-26.md) | Release pin, runtime, power configuration, backups, and engine rebuild |
| [Post-update drive and boot repair](docs/JETLINK_DRIVE_2026-09-26.md) | Short-drive results, DNS retries, startup fix, and remaining validation |
| [Earlier device review](docs/DEVICE_LOG_ANALYSIS_2026-09.md) | Historical platform observations and storage concerns; predates the update |

From a development checkout, summarize a saved JetLink server log with:

```sh
python tools/analyze_jetlink_log.py jetlink-server.log
```

For qlogs, use the openpilot Python environment with its dependencies available:

```sh
python tools/analyze_comma_routes.py '/path/to/extracted/*/qlog.zst'
```

The server analyzer summarizes logged slow-frame warnings, not every inference. The route analyzer reports sampled model metrics, mode transitions, and event-message counts. Raw routes and device logs can contain location, video, CAN, and identifiers; keep them in ignored `diagnostics/` rather than committing them.

## Vehicle scope and credits

Vehicle support, including Honda Clarity and modified-EPS behavior, depends on the exact fingerprint and firmware. This repository provides a gated host profile for the reviewed Clarity PTC files; it does not flash EPS firmware or certify physical steering behavior. See the project's [safety documentation](docs/SAFETY.md) and [limitations](docs/LIMITATIONS.md).

Built on [sunnypilot](https://github.com/sunnypilot/sunnypilot), [comma.ai openpilot](https://github.com/commaai/openpilot), and [Zoompilot JetLink](https://github.com/zoompilot/jetlink), including the accelerator integration from sunnypilot [PR #2001](https://github.com/sunnypilot/sunnypilot/pull/2001). See [LICENSE](LICENSE) and [LICENSE.md](LICENSE.md) for the applicable notices.
