# Clarity-NRDR EPS integration

This repository contains Clarity-Pilot's software base plus a gated NRDR-derived
PTC steering profile for Honda Clarity TRW-A020. It does not alter Clarity-Pilot.

## Source provenance

- Clarity-Pilot base: `98fdb45db2f491e928d2c5eb95539a6045b95d02`.
- Vendored opendbc base: sunnypilot/opendbc
  `f95f996f5917dcbbf2e32fe51b606a24cf836af6`. Local changes live in
  `opendbc_repo`; no external opendbc branch is needed to retain this port.
- NRDR reference: nrdr/openpilot `nrdr-clean`,
  `b3366b5b56512805be8f0bf832b4981bfd958072`.
- Rack table, integral scheduling, phase latch and output filter are adapted
  from that reference. Existing MIT notices and licenses are retained.

## Firmware selection

The supported image is NRDR's
[`ClarityMax-PTM.rwd`](https://github.com/nrdr/openpilot/blob/b3366b5b56512805be8f0bf832b4981bfd958072/openpilot/nrdr/tools/eps/rwd/39990-TRW-A020%20(Honda%20Clarity)/Proper%20Torque%20Mod/ClarityMax-PTM.rwd),
with SHA-256:

```text
d4fe903bcf347495f4321be65a3c650c8c931f1650c3bef6443721da0dd80f7d
```

PTC is **off by default**. After confirming that this exact calibration is
installed, use **Vehicle settings → Honda → Clarity PTC Firmware Installed**
while offroad, then restart the device. A compatible modified EPS identity must
already have been observed before the setting can be enabled in the UI.

Activation requires all of:

1. Honda Clarity fingerprint and Honda brand.
2. At least one EPS identity, with every observed EPS identity equal to
   `39990-TRW,A020` or `39990,TRW,A020` (optional trailing NUL padding).
3. Explicit `HondaClarityPtcFirmware` confirmation.

The comma marker is shared with old torque modifications. **The setting is a
human confirmation, not cryptographic detection of the installed calibration.**
A legacy image with the same reported identity cannot be distinguished over
the existing firmware query. Confirm the image from the flashing record first.

Stock, unconfirmed legacy, unknown and conflicting identities retain the
original profile. Turn this setting off before returning to legacy firmware.
The setting can be disabled offroad even if the rack is unavailable.

No firmware is flashed by startup or by this setting. This repository ships
software support, not a flashing workflow. NRDR's catalog has no Clarity stock
recovery image; obtain the exact rack's verified recovery procedure/image
before any separate flashing operation.

## Steering behavior

The PTC profile uses a linear `[0,3840] → [0,3840]` command map and static PID
`kp=0.03`, `ki=0.01`, `kf=0.000012`. These command values are not physical
torque measurements. The existing generic torque and NNLC selections cannot
replace the PTC PID.

Firmware Table-A geometry maps desired linear angles into physical steering
angles and measured physical angles back into the vehicle model's linear
domain. The base ratio is latched from CarParams (16.5 for Clarity), rather than
allowing a learned ratio to silently replace this geometry during a drive.
Learned stiffness and angle offset retain the base implementation's behavior.

The profile carries NRDR's low-speed integral reset below 2 m/s, base center
boost, low-speed rate damping with unwind taper, and output LPF (0.1 seconds
below 50 mph, 0.05 seconds above). Filtering occurs before carControl publishes
the request, avoiding a false safety-limiting signal from filter lag.

This port deliberately retains the stock 1200 driver-torque takeover threshold.
Driver takeover immediately resets PID/filter state and sends zero torque with
the LKAS request cleared. Steering returns through a 0.1-second ramp.
No 0.28-second override delay or adjustable higher threshold is enabled.

Stock standstill/minimum-speed policy, longitudinal controls, braking and
panda safety code are unchanged. NRDR's standstill expansion, experimental
learners, live P/I/F controls, stiction experiments, torque blending and
longitudinal/radar modifications are outside this initial Clarity profile.

## Validation and qualification

The Linux test suite exercises real Cap'n Proto parameters, Honda interface
construction, PID output, firmware gates, legacy maps, steering geometry and
packed/parsed CAN commands. The existing native Honda safety suite is also run.

```bash
PYTHONPATH=opendbc_repo:. python -m pytest -q -o addopts=   openpilot/sunnypilot/ptc/tests   opendbc_repo/opendbc/sunnypilot/car/honda/test_honda.py   opendbc_repo/opendbc/car/honda/tests/test_honda.py   opendbc_repo/opendbc/safety/tests/test_honda.py
```

Dependencies for this focused suite: Python 3.12, numpy, pycapnp==2.1.0,
pycryptodome, tqdm, pytest, cffi and a C compiler. CI runs the same suite.
The remaining submodules and model LFS assets are inherited from Clarity-Pilot.

This is a source-tested experimental port. No installed-EPS readback,
comma hardware build, recorded-drive replay or vehicle validation was available
for this shipment. Software tests do not qualify the physical steering response.

Before vehicle use, establish the exact rack and calibration, build on the
target comma, check restart/profile selection and faults while parked, and
validate takeover, saturation, low-speed transitions and oscillation in
supervised controlled testing. Review logs before expanding testing.

The inherited Honda safety steering hook blocks nonzero torque when lateral
control is disallowed; it does not independently validate PTC physical torque
authority or steering slew. Its passing regression suite is not a certification
of the custom EPS firmware.
