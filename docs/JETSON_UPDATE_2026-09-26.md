# Jetson update to JetLink v0.4.0 — September 26, 2026

Follow-up: [short drive results and verified boot-order repair](JETLINK_DRIVE_2026-09-26.md). The checks below describe the initial installation; the later report records the subsequent drive, startup failure, applied CDI dependency, and successful reboot.

## Installation

Updated the desk-powered Jetson Orin Nano Super using the official, release-pinned installer:

```sh
sudo bash install-v0.4.0.sh --ref v0.4.0
```

Sources: [v0.4.0 release](https://github.com/zoompilot/jetlink/releases/tag/v0.4.0), [release-pinned update guide](https://github.com/zoompilot/jetlink/blob/v0.4.0/docs/releasing.md), and [Jetson setup](https://github.com/zoompilot/jetlink/blob/v0.4.0/docs/jetson.md).

The Jetson already had JetPack 7.2.1 / L4T 39.2.1; no OS reflash was needed. The release supports this platform. Earlier recommendations to revert this device to JetPack 6 describe an older JetLink deployment and do not apply to v0.4.0.

| Item | Result |
| --- | --- |
| Release source commit | `3e6a59f9fcae28abaf942e66d6e8758afa6103c9` |
| Installer SHA-256 | `4d3f99c0617dd5743d816827fbd2346ee4eebbb1ae4488fc7347905ba3753117` |
| Container | `ghcr.io/zoompilot/jetlink:0.4.0-cuda` (ARM64) |
| Installed image ID | `sha256:35c0be8c9bb519c9c67d22d55e2c0eb36516a10a45c143e42b08393a5ea4884d` |
| Runtime GPU probe | Orin, compute 8.7, TensorRT 10.16.2.10 |
| Power mode | MAXN_SUPER, explicitly requested by the owner; active mode 2 |
| Power behavior | Switched with the car; suspend timer disabled |
| Service | Enabled at boot; new installer-managed launcher |
| Cache | Existing `/mnt/data/jetlink` retained |
| Swap | Existing 8 GB file retained |

The installer also masks network wait-online units and limits the system journal to 200 MB. Docker 29.8.1 and the existing NVIDIA runtime were reused. The existing nvpmodel service dependency was preserved. Despite its `25w-startup.conf` filename, that drop-in only orders/requires nvpmodel; it does not force the old 25 W mode. Saved nvpmodel state now records mode 2.

## Recovery and compatibility

Before installation, saved the old service definitions, power configuration, fstab, USB-wake setup, image metadata, and `/etc/jetlink` in a timestamped backup directory on the Jetson. The previous container image remains available, and the installer also saved `/etc/jetlink/server.env.prev`. Preserve the complete service backup when reverting this legacy-to-installer migration; replacing only the image setting would leave the new launcher and its defaults in place.

The comma remains on its existing custom build. Its installed JetLink protocol file is byte-for-byte identical to v0.4.0 (SHA-256 `1da63949470c776cd9ced15418eebb8323aa3cdd53c65a47a5dc1ce22796b2a5`, protocol version 2). This rules out a wire-version mismatch, but does not establish complete fork compatibility. No comma software or model selection was changed. USB pairing and driving validation remain separate checks once the devices are connected while parked.

The installation is pinned to `v0.4.0`. `jetlink update` keeps that saved ref; it does not automatically advance to a later release. Use the official installer with an explicit newer `--ref` when a later upgrade is intended.

## Model preparation and final checks

The previously loaded model was Cinque Terre Model (September 04, 2026), ref `68b5f8e48602f4f88041efd7de6c99e97fda454e`, ONNX SHA-256 `e8d821733be15ebe9e27498bc27ad8bbbd741980ece37d77f377294010b8ff28`. Its old TensorRT 10.3 plan could not serve as the new runtime's cached engine. Stopped the server, ran `jetlink models prepare` for that same ref, and restarted it. The build completed successfully in 185.1 seconds; the original model downloads and old plans were retained.

Final live checks at approximately 21:23 UTC:

- Container package metadata reports JetLink **0.4.0**, TensorRT **10.16.2.10**.
- The service preloaded the rebuilt engine, captured its CUDA graph, and reported **engine ready** at 21:23:13 UTC.
- Service state: active/running, `NRestarts=0`, enabled at boot.
- MAXN_SUPER active, GPU pinned at 1,020 MHz, CPU at 1,728 MHz, EMC at 3,199 MHz.
- The installer did not request a reboot. Saved power-mode state was checked; a cold-boot test has not been performed.
- The comma is not physically connected. No USB inference session, end-to-end latency measurement, or road validation was performed.

Private before/after backups and installation/build logs are stored on the Jetson under its user's `jetlink-backup-20260926-v040` directory and copied into ignored local `diagnostics/jetlink-v0.4.0/`. They are excluded from Git.
