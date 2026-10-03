# October 3 drive: Cinque Terre V2 on JetLink v3

The updated comma joined the Jetson at **+28.21 seconds** and recorded **6,071 consecutive large-model outputs** over the following **303.5 seconds**. No return to the small model, large-model frame-ID gap, or unexpected managed-process stop was recorded. This supports one short drive on the updated deployment; it does not establish long-term reliability.

## Capture and configuration

Six full-rate `rlog` segments and their six sampled `qlog` companions cover **331.80 seconds**. Recent comma application logs, the Jetson's retained service journals, and its new desk-boot logs were also collected. Raw captures remain in ignored `diagnostics/2026-10-03-drive/`; this report omits route identifiers, locations, network addresses, vehicle identifiers, and raw CAN data.

The drive identifies deployment commit [`8cde0c0a5`](https://github.com/ryanafdahl/openpilot/commit/8cde0c0a52ef472f4e792963399959524c93416c), on the `Clarity-Pilot` branch of the device repository. It includes all eight sunnypilot updates through `a5f44653d`, JetLink **0.8.0 / protocol v3**, and tinygrad `f6fc4e3f2`. This is the separate device deployment, not a claim that every source-checkout feature was road-tested.

The client identified **Orin-sm87 / TensorRT 10.16.2.10**, establishing that this drive used the NVIDIA Jetson rather than the Pixel. Cinque Terre Model V2 was the configured large model. The Jetson's subsequent desk boot confirmed the cached `09d080f36965bb2a` V2 engine. CD210 remained the comma's selected small model. The Pixel was not qualified by this drive.

## Full-rate results

| Measurement | Result |
| --- | --- |
| Recording span | 331.80 s |
| Small-model outputs | 364 |
| Large-model outputs | 6,071 |
| First large-model output | +28.211 s |
| Large-model execution, mean / median | 25.77 / 25.63 ms |
| Large-model execution, p95 / p99 | 27.24 / 27.95 ms |
| Maximum large-model execution | 52.36 ms, at the initial join |
| Large-model executions over 50 ms | 1 of 6,071; the join frame |
| Large-model publication interval, mean / maximum | 50.00 / 54.91 ms |
| Large-model frame-ID increment | Exactly 1 between all 6,070 adjacent outputs |
| Reported large-model `frameDropPerc` | 0 throughout |
| Return to small model after joining | None recorded |
| Required process reported not running | None recorded |

**These are comma-reported model execution times, not pure GPU timings.** `modeld` measures the model-run call, including the client path. Camera EOF to model publication averaged **50.72 ms** (p95 **52.25 ms**, maximum **77.31 ms**); this is a separate pipeline measurement and is not camera-to-control or actuator latency. A publication interval slightly above 50 ms is not, by itself, evidence of a missing camera frame.

The sampled qlogs contained 607 large-model observations and a maximum of only **30.29 ms**. They missed the **52.36 ms** join frame found in the full-rate data. This is why the conclusions above use rlogs rather than treating the qlog maximum as the drive's maximum.

## Startup and join timeline

Times below are relative to the beginning of this recording, not Jetson power-on.

| Time | Evidence and interpretation |
| --- | --- |
| +0.21 s | Offroad `jetlinkd` stopped normally as onroad model processing took ownership. Its exit code was zero. |
| +8.65 s | The client reported preparation of the large-model path in 2.70 s. |
| +9.97 s | First small-model output: **1,282.87 ms**, marked invalid. |
| +20.38 s | Initial join attempt failed with `No such device`; the client scheduled its five-second retry. |
| +25.41 s | Gadget presented again, waiting for enumeration. |
| +26.82 s | Handshake identified the Orin and TensorRT runtime. |
| +28.14 s | Link ready; waiting for a permitted swap window. |
| +28.21 s | First successful large-model output and transition from `joining` to `running`. |

The startup small-model frame was the only small-model execution over 50 ms. Its next published frame advanced by 27 camera frame IDs, implying **26 skipped IDs at startup**, even though the reported drop percentage remained zero. The first result was invalid; subsequent validity flags were true. This is not evidence of dropped frames during steady large-model operation.

The first large-model frame took **52.36 ms**. Nearby client diagnostics reported approximately **1.9 ms warp**, **3.2 ms data preparation**, **5.2 ms send**, and **24.5 ms reply wait**, with server-reported GPU time **23.3 ms**. These component diagnostics are useful context, not a complete accounting of every part of the enclosing model-run timer. The code builds the large-model state at the swap and carries a reset on its first real frame; the timing is consistent with a join cost. It does not prove a single exclusive cause.

Both execution outliers occurred while selfdrive was disabled. Two later enabled intervals total approximately **59.36 seconds**. The early `No such device` error was a recovered pre-join condition; it was not a loss of an already-running large model. The available evidence does not identify whether boot timing, cable enumeration, or another initial USB condition caused it.

The first `modelV2` and `modelDataV2SP` messages were invalid; the remaining **6,434 of each** were valid. `bigModelAvailable=false` while the accelerator is running is expected: that field describes a waiting-to-swap model, not proof of current execution. `modelV2.big` and `acceleratorState=running` provide that evidence.

## Jetson telemetry and other observations

The comma retained **290 Jetson telemetry samples**, all with the client marked alive:

| Telemetry | Median | Maximum |
| --- | --- | --- |
| Reported temperature | 60.2 °C | 61.9 °C |
| Reported power | 12.15 W | 13.74 W |
| Memory temperature | 58.8 °C | 60.6 °C |
| GPU clock | 1,020 MHz | 1,020 MHz |

GPU clock samples ranged from 918 to 1,020 MHz. The desk query still identifies **MAXN_SUPER, mode 2**; the telemetry's `power_limit_w=25` field should not be treated as proof that nvpmodel was switched to a 25 W profile. These samples do not establish a sustained thermal limit or a universal power requirement.

No `modeldLagging`, `selfdrivedLagging`, `commIssue`, or `commIssueAvgFreq` event was recorded. There were startup location-estimator resets, an `athenad` receive exception around +80 s, and a GNSS almanac write NACK near the end. They did not coincide with a large-model fallback or recorded lag event. The almanac message concerns receiver state storage; this analysis does not establish a GNSS positioning failure. No driving-code changes were made in response to this one recording.

## What the Jetson journal can and cannot confirm

After the drive, the Jetson was moved to the desk and powered on independently. Its current service was active, with **zero automatic restarts**, and loaded the V2 engine at **11.26 seconds of monotonic boot time**. Waiting for a USB gadget at the desk is expected because the comma was not attached there.

The retained journals did **not** yield a native-server record for this drive, even after boot-specific and individual archived-file queries. The prior journal file examined passed journal verification. Early timestamps include an unset wall clock, so calendar ordering is unreliable; monotonic timestamps were used for the desk startup measurement. The reason the drive's server journal was not recoverable remains unconfirmed.

Consequently, the drive conclusions rest on the comma's complete recorded model stream, client diagnostics, and returned Jetson telemetry. There is no independent full-drive server-side GPU timing distribution, and the **11.26 s desk boot must not be substituted for the drive's Jetson boot time**. Capture or export the server journal before the next power removal if that evidence is needed.

## USB Wi-Fi retirement

At the owner's request, the external dongle's **rtl8821au 5.12.5.2** driver was unloaded and removed from DKMS for the installed kernel. Its module is no longer found by `modinfo`, its DKMS registration is absent, and its source was moved out of `/usr/src` so automatic DKMS rebuilding cannot reinstall it. No separate dongle-specific startup service or module-load entry was found.

Ethernet remained connected and `jetlink-server.service` remained active. The existing onboard-radio blacklist was retained because its note documents damaged internal antenna connectors; removing the external dongle does not repair those connectors. Generic networking services and the DKMS utility were retained.

A root-owned rollback copy is at `/var/backups/clarity-pilot-usb-wifi-20261003/`, containing a source archive and `source-disabled/`. Recovery, if deliberately requested later, consists of restoring that source to `/usr/src/rtl8821au-5.12.5.2`, then running `sudo dkms add -m rtl8821au -v 5.12.5.2` and `sudo dkms install -m rtl8821au -v 5.12.5.2`. A reboot was not necessary to unload and remove the unused module; this cleanup has not yet had a separate reboot test.

## Remaining checks

- Repeat a cold car power cycle and a longer drive, keeping the server journal before powering the Jetson down.
- Investigate small-model first-frame initialization if its delay remains objectionable; one run cannot establish its typical cost.
- Complete Pixel model preparation, benchmark, output parity, and direct-USB qualification separately.

This drive demonstrates a successful late join and continuous recorded large-model output for about five minutes. It does not validate every failure mode, the vehicle's modified EPS, or uninterrupted engagement after a future link failure.
