# JetLink 0.8.12 parked validation — November 1, 2026

The comma's JetLink 0.8.12 installation passed the adapter checks, a real
ignition-off reboot, and the subsequent parked USB/inference check. The owner
reported no returning dashboard warnings and a green GPU icon. Full-rate logs
support that observation over a **70.751-second stationary session**.

This result covers startup and inference while parked. Controls remained
disengaged; it does not qualify driving behavior or establish the cause of the
October 31 dashboard warnings.

[Machine-readable technical aggregates](validation/jetlink-parked-2026-11-01.json)
exclude raw routes, location, device identifiers and connection credentials.

## Configuration and installation

| Item | Evidence |
| --- | --- |
| Recorded comma source | `87d9989d29d89fcb61eef8a5d6477d493ac45b8f` |
| JetLink client | 0.8.12, pin `a863c3801da6fd925d14eb1f5b1e250f8efcc649` |
| Protocol / adapter API | 3 / 3; adapter conformance returned no errors |
| Jetson server | 0.8.12 from prior direct verification and owner confirmation |
| Recorded peer | Orin-sm87, TensorRT 10.16.2.10, USB SuperSpeed |
| Saved small / large model | Pop Model v2 / Cinque Terre Model V2 |
| Large-model hash | `09d080f36965bb2a0790500452bd328aa03c484d0222aa79d1ad9f021a522aec` |
| Adapter regression suite | 119 passed, 3 skipped |

Installation and reboot occurred with ignition off. Model selections, PTC
confirmation, link mode, charging and update preferences were preserved. Fresh
post-reboot Panda/device/manager messages were healthy, with no unexpected stopped
services. Vehicle control tuning, Panda safety and EPS firmware were unchanged.

The Jetson was already powered off when logs were retrieved. Its runtime identity
and model-pick record are from this session; its installed version is supported
by the prior direct check and owner confirmation, rather than a new live server
query after shutdown.

## Startup and inference

The first handshake read timed out at 20.055 seconds. An automatic five-second
retry and gadget endpoint re-enumeration followed. The link was ready at 27.714
seconds and the large model began producing output at **27.761 seconds**.

| Large-model metric | Result |
| --- | ---: |
| Full-rate output frames | 860 |
| Approximate operation after joining | 43 seconds |
| Mean execution | 23.532 ms |
| p95 execution | 24.122 ms |
| Maximum execution | 31.218 ms |
| Frames over 50 ms | 0 |
| Small-model frames after the large-model join | 0 |
| Maximum reported frame-drop percentage | 0% |

These are model-runtime measurements, not camera-to-publication latency or an
independent accounting of every camera frame. The small model produced 370 frames
before handoff, including one **1.386-second initial warm-up frame**; all its
remaining frames were below 50 ms.

## Vehicle and Panda observations

- All 6,295 carState samples had no ACC fault, CAN timeout, temporary/permanent
  steering fault or noncritical stock-camera fault. CAN validity became true at
  7.650 seconds, after 15 initial startup samples.
- Neither brake-error bit was asserted in 7,061 decoded HYBRID_BRAKE_ERROR
  messages. ACC_PROBLEM and FCM_PROBLEM remained zero.
- The camera LKAS startup indicator cleared at 2.130 seconds, and the brake-system
  icon bit cleared at 5.127 seconds. Neither recurred. The raw startup flags were
  therefore not all zero.
- No accFaulted, controlsMismatch, radarFault, commIssue, commIssueAvgFreq or
  selfdrivedLagging event occurred. Initializing, model-loading, Park, seatbelt,
  parking-brake and pre-enable-standstill events were recorded.
- All 702 Panda samples had no internal fault or heartbeat loss. Six attempted
  transmissions were rejected in diagnostic ELM327 mode before Honda Nidec mode
  began at 10.582 seconds; the blocked counter then reset to zero. No invalid
  receive-check interval was recorded.
- Speed remained zero, gear was Park after initialization, and carControl
  enabled/latActive/longActive remained false.

Ignition went off at 70.639 seconds. USB disconnected at shutdown and modeld
returned the gadget. Subsequent offroad/disconnected status is consistent with
the owner powering the car and Jetson off.

## Scope and remaining limits

Two full rlog segments and their two qlogs were retained privately. The full rlogs
were analyzed; the qlogs were not used as a substitute for full-rate timing or
fault observations. Raw logs were not published.

The previous 0.8.7 rollback remains available at
`be330d9470ec58a527a4a890effe7a677668106d`. The earlier warnings cleared during a
separate parked session on that rollback. This subsequent successful 0.8.12
startup shows that the observed faults did not recur in this check; it does not
prove why they occurred previously. No ECU trouble codes were cleared, fault flags
masked or safety checks relaxed for either check.

This publication changes documentation only. The installed device revision and
the tested JetLink source remain as recorded above.
