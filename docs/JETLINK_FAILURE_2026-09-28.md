# JetLink connection failure — September 28, 2026

## Result

The comma evidence confirms no large-model operation in any of today's five recorded drives. Paired logs and deployed code identify a missing comma readiness marker as the leading explanation, following the previous evening's Pixel parked test. The Jetson successfully loads its engine, but the comma's missing marker prevents its onroad JetLink connection path from starting. A connected parked recovery test remains necessary. The Jetson is currently at the desktop and disconnected from the comma; current USB absence is expected.

## Evidence collected

Collected 712 application logs and 185 qlogs into ignored `diagnostics/2026-09-28-no-jetlink/`, plus a live comma snapshot, kernel USB events, deployed-code excerpts, and route-analysis JSON. The archive contains 897 files (99,261,202 bytes); SHA256 is `D6C1A35F47198B25D74F4E615A881562FC21654B453340976648B90EC9B2140B`.

Selection begins September 28 at 07:00 UTC (midnight PDT), using file modification times. Application-event times below are PDT. Jetson logs were subsequently retrieved over Ethernet at 192.168.1.187 after authenticated login. No device settings, services, or software were changed.

The comma runs deployed commit `d57c4b533558bb2314f542a2ea78c3271b265eda`. Live `JetlinkEnabled=1`, cached model specification exists, gadget setup marker is `ok`, and the offroad jetlinkd process runs. `JetlinkEngineReady` was absent from the live parameter listing. These are capture-time observations, not a reconstruction of every drive-time parameter.

## Recorded drives

The existing `tools/analyze_comma_routes.py` ran in the comma's openpilot Python environment. All 185 qlogs parsed without errors.

| Drive order | Approximate start PDT from modeld | Segments | Recorded span (minutes) | Small-model samples | Large-model samples |
| --- | --- | ---: | ---: | ---: | ---: |
| 1 | 05:41 | 5 | 4.20 | 493 | 0 |
| 2 | 05:48 | 54 | 53.62 | 6,424 | 0 |
| 3 | 11:21 | 39 | 38.48 | 4,606 | 0 |
| 4 | 12:01 | 11 | 10.78 | 1,283 | 0 |
| 5 | 15:37 | 76 | 75.28 | 9,023 | 0 |

Total: 21,829 small-model samples over approximately 182.36 recorded minutes. Qlogs are sampled evidence, not every inference frame. There are no observed transitions to the large model. The last drive's small-model execution mean is 28.61 ms, p95 30.18 ms, with a 2,051 ms maximum; this maximum alone does not diagnose the connection failure.

## Connection timeline and indicator

Application logs record `gadget presented, waiting for a jetson` at 05:46:02, 06:41:36, 11:59:28, 12:12:09, and 16:52:19. The captured day's JetLink events contain no successful attach, engine-ready, or Jetson telemetry event. Manager stopping jetlinkd at drive startup is the normal offroad/onroad process handoff and does not itself prove a crash.

Kernel logs show repeated Type-C source connections and disconnects during the morning, starting at 05:41:57. The afternoon shows connections at 15:38:23 and 15:38:52, with disconnects at 15:38:46 and 15:40:18. These establish electrical Type-C connection changes, not successful JetLink protocol communication or the identity of the attached host. Some USB power-delivery log entries say `pd_phy_signal: failed ret 0`; those messages alone do not establish the root cause.

The deployed helper requires the USB device controller to reach `configured` before reporting an attached host. The deployed UI returns `DISCONNECTED` when no accelerator is present, even onroad; a detected pending join can instead show `LOADING`. This explains why no blinking indicator is consistent with a failure before recognized accelerator attachment, rather than merely a long model build.

The deployed stock modeld also gates JetLink startup on `accelerators.ready()` and `accelerators.prepare()`. Readiness requires the matching engine-ready marker. A cached model specification alone does not satisfy that gate. This provides a plausible explanation for ordinary small-model startup without connection retries once provisioning has not completed; historical readiness values were not recorded directly in this capture.

## Jetson evidence recovered

Retrieved service definitions/status, retained service journal, filtered syslog, recent unfiltered syslog, dmesg, container logs, and boot records. Archive `jetlink-diag-20260928.tar.gz` SHA256: `E3D49DA5C199A437AD68CA73CDC88F8CBF65261CC1391357975CBCF5E8E5CC96`. Additional boot context is in `jetlink-diag-20260928-extra.tar.gz`.

The desktop boot has active JetLink, successful nvpmodel, successful CDI generation, and the installed `20-after-nvpmodel.conf` ordering fix. The container loads TensorRT 10.16.2.10 and the expected `e8d821733be15ebe` engine, captures its CUDA graph, and reports engine ready. It waits for USB gadget `1209:0001`, as expected while disconnected.

After the last inference-bearing boot in retained syslog, seven successive boot blocks contain successful nvpmodel initialization and no comma gadget enumeration. Six contain explicit engine-ready messages; one block ends after service start without a readiness result. None of these seven blocks shows nvpmodel failure. See `syslog-filtered.txt` lines 11456-11820. Their unset/reset clocks prevent assigning exact September 28 drive times or treating the journal boot list as complete. These logs do not support recurrence of the earlier nvpmodel/CDI failure. They also do not independently rule out a physical USB fault.

## Readiness loss after the Pixel test

The previous evening's comma logs identify the connected server as `Pixel 11 Pro XL / Tensor G6 trt None`. At 19:43:29, normal JetLink provisioning fails with `engine build failed: Model accuracy unqualified: parked test client and exact model required`. That message is emitted by the Pixel test app. The generic log wording `jetson attached` therefore must not be treated as proof that this was the NVIDIA device.

At **20:09:57.221 PDT on September 27**, jetlinkd logs `disabled, releasing the link`. The verified deployed `jetlinkd.step()` branch immediately calls `helpers.set_engine_ready(None)`, removing `JetlinkEngineReady`. At 20:12:02, the daemon restarts; at 20:12:03 it presents the gadget and waits for a host. No subsequent engine-ready success appears in the collected readiness history or September 28 application logs. The marker remains absent during live inspection, while `JetlinkEnabled=1`.

The local parked-test helper `tools/pixel_jetlink/parked_comma.py` saves `JetlinkEnabled`, disables it to release USB for the isolated test, then restores only that saved enable setting. It does not preserve or re-establish `JetlinkEngineReady`. The adjacent Pixel project's recorded September 27 test result confirms that the enable setting was restored to 1 afterward. The timing, log messages, and helper behavior strongly support a test cleanup side effect; there is no need to assume the owner manually changed the setting.

The resulting startup sequence explains today's symptom:

1. The readiness marker is absent, even though the Jetson's cached engine still exists.
2. Manager stops the offroad jetlinkd daemon when the drive starts.
3. Stock modeld checks `accelerators.ready()` once at startup. With no marker, it does not create the JetLink joining model or present its USB gadget.
4. A Jetson that becomes available after that transition cannot complete offroad provisioning or join this modeld instance. The small model runs, and the UI has no configured accelerator to show as loading.

This is a software readiness/reconnection gap. It explains the consistent all-small-model drives and missing indicator, and is more directly supported than a GPU or TensorRT failure. Historical per-drive readiness values and paired USB traces are incomplete, so a connected test is still required to establish the full causal chain and exclude an additional cable/port issue.

## Recovery and remaining validation

With both devices connected by USB and powered, keep the comma offroad long enough for its normal daemon to detect the real Jetson and verify the cached engine. Confirm an `engine ready` event and a matching `JetlinkEngineReady` value before testing a subsequent drive transition. Do not manufacture a readiness marker simply to bypass verification.

The repair below addresses both the parked-test cleanup side effect and the onroad inability to reconnect without a pre-existing readiness marker. Connected validation remains pending.

## Repair installed September 28

- Stock modeld now starts the joining path when JetLink is enabled, matching the selected-small-model runner, instead of requiring the readiness marker at startup. Existing cached-spec/selected-model checks and the server handshake still apply.
- Disabling JetLink releases USB and clears session state without deleting the verified engine identity. Each new attachment still verifies the server; disabling does not delete its engine cache.
- A successful onroad engine handshake restores the readiness marker. Failed handshakes do not set it; an explicitly missing engine still clears it.
- The older deployed build also needed the existing public `accelerators.enabled()` wrapper from the source repository.

Deployment commit on the comma: `33dbae4ebcc8e73a530d5ab15bd713f490e4c60e`. Original files, the base commit, patch, and test output are retained in `/data/jetlink-repair-20260928/`. No unrelated Pixel project files were changed.

Validation on the parked comma: 150 regression tests ran successfully, with three baseline-comparison tests skipped because the `develop` reference was unavailable. Tests used `OPENPILOT_PREFIX=jetlink_repair_test` to isolate parameters. Coverage includes disabled-link behavior, native accelerator isolation, missing-readiness startup, marker preservation, handshake success/failure, late join, disengagement gating, and fallback. Changed production files pass Python compilation and `git diff --check`. Live checks confirm JetLink enabled, selected/cached model identities matching, cached warp available for `(1344, 760, 512, 256)`, and no gadget setup error. The missing readiness marker was deliberately not fabricated.

After explicit owner approval, both branches were published and their remote heads verified: source repair `30f613d920c92bd6f7c3026d02ed024632d66af3` on `ryanafdahl/Clarity-Pilot` main, and deployment `33dbae4ebcc8e73a530d5ab15bd713f490e4c60e` on the `ryanafdahl/openpilot` deployment branch. The installed commit is also retained locally under `refs/remotes/comma/readiness-fix`. A connected parked test and subsequent drive transition remain required; unit tests do not establish end-to-end USB operation.

The parked comma was gracefully rebooted and verified at deployment commit `33dbae4eb` with a newly running jetlinkd, `IsOffroad=1`, and gadget setup marker `ok`. The launcher's Git-modification guard prevented the older staged update from replacing the repair. Final Jetson checks confirmed the inference service active and nvpmodel successful before transport to the car.
## Post-repair test drive — September 28

The owner observed the GPU icon change from blinking white to green while parked, then completed a short drive. All six qlogs and eight application logs were retrieved under ignored `diagnostics/2026-09-28-repair-drive/`. All qlogs parsed without errors and identify deployed commit `33dbae4ebcc8e73a530d5ab15bd713f490e4c60e`. Live Git status after the drive was clean.

The recording spans 303.09 seconds: 58 small-model samples, followed by 529 large-model samples beginning at +38.83 seconds. There is no sampled return to the small model. Recorded onroad events contain no modeldLagging, selfdrivedLagging, commIssue, or commIssueAvgFreq message.

Large-model execution mean/p95/maximum: 30.91/32.13/40.58 ms. The reported frame-drop field is zero in every sampled message. Across 250 telemetry samples, all report dead=false; GPU temperature ranges from 35.2 to 57.1 C, clock remains 1,020 MHz, reported supply is 4.928–4.976 V, and power is 9.12–12.66 W.

At 18:31:21 PDT the initial connection attempt had no USB reader and scheduled a retry. At 18:31:26 the comma waited for host enumeration; at 18:31:33 the server answered; at 18:31:34.949 the link was ready; at 18:31:35.043 the large model joined. Its first three server GPU timings were 17.7–17.8 ms. No connection-loss or fallback event appears after the join in the captured application logs. The offroad daemon presented its gadget again at 18:36:00.486.

This validates late connection and sustained large-model operation for one short drive. Qlogs are sampled evidence; zero in the reported frame-drop field does not prove every frame met its deadline. Repeated cold starts and longer drives remain untested. No device changes were made during this post-drive analysis. The owner explicitly approved publication of these test-drive findings.
