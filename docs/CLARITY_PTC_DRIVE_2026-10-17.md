# First reviewed Clarity PTC drive — October 17, 2026

The owner reports flashing `ClarityMax-20260928-Pminus5-A280Flat-KFF45-Tracker3200-Norm1650-3840.rwd`, enabling PTC in the comma 4 UI and driving. The supplied local file still matches SHA-256 `9e2e98857a6734f4631205cb9550bf7cb61720da566a4c117b9187a8ddf25d61`. The existing EPS firmware query identifies TRW-A020 but cannot distinguish this calibration from older modified images. No EPS calibration readback was performed.

The drive recording confirms the **host PTC profile was active**: `HondaClarityPtcFirmware=1`, `CLARITY_PTC` set in every recorded extended CarParams, PID `kp=0.03`, `ki=0.01`, `kf=0.000012`, fixed base ratio 16.5 and linear `[0,3840] → [0,3840]` commands. Its software commit is `9c17798b15c62ffc2310d51734b5794cf7bc2bdc`. The preceding recording has PTC off and the original 3x command map. This is recorded deployment evidence, not full vehicle qualification.

## Recording coverage

Downloaded **25 full-rate logs and 25 compact logs** from two retained recordings. Every downloaded file matched its source SHA-256 and size. All full-rate segments parsed without errors or warnings. The preceding recording spans **538.53 seconds (9 segments)**; the PTC recording spans **910.22 seconds (16 segments)**. Raw logs, route identifiers, location, VIN, device identifiers and credentials remain private. Public measurements are explicitly selected aggregates.

| Measurement | Preceding legacy 3x recording | First PTC recording |
| --- | ---: | ---: |
| Large-model outputs | 10,250 | 17,681 |
| Small-model outputs before joining | 254 | 304 |
| Large-model execution mean / p95 / max | 23.58 / 25.04 / 38.32 ms | 23.41 / 24.77 / 31.98 ms |
| Camera-to-publication p95 / max | 50.12 / 62.95 ms | 49.63 / 56.45 ms |
| Camera-to-publication over 50 ms | 627 / 10,250 | 461 / 17,681 |
| Largest large-model frame-ID increment | 1 | 1 |
| Large-model outputs marked invalid | 0 | 0 |
| Missing expected process samples | 0 | 0 |

Different roads, speeds and driver input prevent treating this as an improvement measurement. Reported model execution and camera-to-publication are distinct quantities; 23.41 ms execution does not imply a 23.41 ms control pipeline.

## JetLink and startup

The comma client pin is stable **JetLink 0.8.7**, protocol 3, adapter API 3. Current upstream checks still point to JetLink 0.8.7 and NRDR `nrdr-clean` at `b3366b5`; no newer release was available to install. The Jetson server was last checked live as 0.8.7 earlier the same day. The PTC drive's handshake identifies **Orin-sm87 / TensorRT 10.16.2.10**, and the resident owner records USB **super-speed** enumeration. CD210 and Cinque Terre V2 selections were preserved.

One startup attempt failed with FunctionFS `Errno 19` during USB enumeration, then retried. The large model joined **26.10 seconds** after recording start and remained large through the recording's end. All **17,680 successive large-model frame-ID increments were 1**; reported frame-drop percentage stayed zero. There was no observed large-to-small fallback after joining. Jetson telemetry ranged from **52.6 to 63.5 °C**; comma thermal status stayed `ok`.

The first small-model output took **1,433.23 ms**, was marked invalid and occurred while lateral control was inactive. The earlier drive had the same startup-only pattern (1,427.48 ms). The remaining small-model p95 was below 30 ms. These startup behaviors remain open for paired cold-boot investigation. The Jetson was switched off when this review began, so no current SSH failure diagnosis, new parked inference test or paired server boot-journal claim is made.

## Steering commands and driver input

Decoded **89,391 outgoing Honda steering messages** in the PTC recording. None exceeded an absolute command of 3840. The maximum logged actuator CAN command was 3807; this is a command value, not measured physical steering torque.

For steady conditions lasting longer than 50 ms, using car/control state fresher than 25 ms:

- **5,536 driver-override steering messages:** torque zero and LKAS request clear in every checked message.
- **11,205 lateral-inactive steering messages:** torque zero and LKAS request clear in every checked message.
- **1,098 EPS-inhibited steering messages:** torque zero and LKAS request clear in every checked message.

These categories can overlap. They validate observed steady release behavior; they do not establish worst-case transition-edge latency or full takeover qualification. No PTC PID nonfinite output or PID saturation was logged during the filtered assisted samples. Approximately **741.55 seconds** met that analysis filter (PID active, recent car state, lateral active, driver steering not pressed).

The `steerFaultTemporary` samples decode to **NO_TORQUE_ALERT_1**: **14 windows, 1,173 car-state samples**, all with recorded driver steering input. The preceding 3x drive also has this status (18 windows, 1,123 car-state samples), so it is not unique to this PTC run. No permanent EPS fault was observed. Zero commands during sustained inhibition were checked above. This correlation does not independently diagnose the EPS's internal reason or replace a diagnostic-code read.

## Tracking and warnings

Across filtered assisted samples, absolute desired-versus-measured steering-angle error had median **0.92°**, p95 **4.91°**, and maximum **270.65°**. The maximum occurs during low-speed re-entry after manual steering, at about **3.16 m/s**, with measured wheel angle about **−321.8°**. Treating that maximum as steady lane tracking would be misleading. In the **10–20 m/s** speed band, median error was **0.77°**, p95 **2.92°** (55,219 samples). The preceding drive's p95 in that band was 0.80°, but geometry/setpoint construction, road and driver conditions differ. No PID retuning is justified by this unmatched comparison alone.

Maximum speed in filtered PTC-assisted samples was **17.82 m/s (39.9 mph)**. The above-50-mph PTC center-boost behavior was not exercised. Oscillation, high-speed behavior and physical torque authority remain unqualified.

Four **stock forward-collision-warning** event samples occur around recording-relative 330–334 seconds while lateral and longitudinal control were active. The large model was running at approximately **22.81–23.00 ms** in those samples. No openpilot-generated `fcw`, `steerSaturated`, `controlsMismatch`, `commIssue`, `commIssueAvgFreq`, `modeldLagging` or `selfdrivedLagging` event was recorded. The logs alone do not establish the traffic cause or appropriateness of the stock warning. Alarm thresholds and safety policy were preserved.

## Update outcome and remaining limits

The comma is parked with ignition off, PTC confirmation on, compatible cached EPS identity, preserved CD210/V2 selections and healthy required offroad processes. The current source already matches the checked NRDR and JetLink stable references. This maintenance updates the deployment/drive documentation and measurements; it does not change steering gains, firmware, driver takeover thresholds, models or CAN safety policy.

The previous source-only qualification statements are superseded by this hardware deployment and one recorded PTC drive. Controlled takeover/re-entry, low-speed behavior, highway operation, oscillation, saturation, cable-loss fallback and repeated cold boots still require separate qualification. No claim of firmware certification or general vehicle safety follows from this recording.

[Machine-readable technical aggregates](validation/clarity-ptc-drive-2026-10-17.json).
