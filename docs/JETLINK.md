# JetLink on Clarity-NRDR

This repository pins JetLink **v0.8.12**, commit
`a863c3801da6fd925d14eb1f5b1e250f8efcc649`, protocol v3, openpilot integration
API 3. The matching [release](https://github.com/zoompilot/jetlink/releases/tag/v0.8.12)
provides Jetson/Linux servers and companion apps. The comma 4 deployment and
October 17 USB 3 drive are now recorded in the
[PTC drive review](CLARITY_PTC_DRIVE_2026-10-17.md). That drive identifies the
Orin/TensorRT peer, 17,681 consecutive large-model outputs and no fallback after
joining. The startup enumeration retry and qualification limits remain documented.

The November 1 ignition-off installation restores the client from 0.8.7 to
0.8.12 after the precautionary rollback and retains API 3.
`Keys.select` names `ModelManager_DownloadRef`, so a newer server-side model pick
also updates the comma's model manager. Existing selected models, PTC confirmation,
and handoff gating are preserved.

The [November 1 parked validation](JETLINK_PARKED_2026-11-01.md) covers the
installation checks, real reboot and subsequent physical USB session. It records
860 large-model frames at 23.53 ms mean execution, with no fallback after joining
or returning ACC/brake fault. The initial handshake retry, brief startup flags
and qualification limits are included. The original dashboard warning cause
remains unconfirmed.

## Install or update the comma checkout

With ignition off, update this repository and its pinned submodules on the comma,
then build and restart using the normal source-install workflow. Check the next
ignition-on/USB session while parked with assistance disengaged:

```sh
git pull --ff-only
git submodule update --init --recursive
```

The startup launcher exposes `jetlink_repo/jetlink` as the Python package.
SCons builds the camera warp in the fork's adapter directory before manager
starts. The warp uses this fork's NV12 graph and tinygrad pin, with the batched
`M_inv` and `input_frame` layout required by v0.8.12. Missing or incompatible
warps keep inference on the small model.

Offroad, choose **Settings → Models → JetLink → USB** for a Jetson, Mac or
Android host, then select the large model in the big-model list. The former
boolean Accelerator Link setting and separate model-name catalog have been
replaced. Review the new setting and model selection after upgrading; do not
copy an old engine-readiness marker into the new parameters.

The small-model selection, original Honda controls, and explicitly confirmed
Clarity PTC firmware profile remain independent of the accelerator selection.
The resident `jetlinkd` now holds the USB gadget across ignition transitions.
API 3 checks fresh car/control messages before a handoff; active openpilot,
MADS, stale messages or a query failure prevent swapping to the large model.
Loss or sustained lag of the large model returns inference to the small model
and raises the existing takeover alert. The small model's history is reset in
place before fallback, including this fork's legacy bundle layouts.

## Companion releases

Update peers separately, while parked, following the pinned upstream guides:

- [Jetson](https://github.com/zoompilot/jetlink/blob/v0.8.12/docs/jetson.md)
- [Linux PC](https://github.com/zoompilot/jetlink/blob/v0.8.12/docs/linux-pc.md)
- [Android](https://github.com/zoompilot/jetlink/blob/v0.8.12/docs/android-app.md)
- [Mac](https://github.com/zoompilot/jetlink/blob/v0.8.12/docs/macos-app.md)
- [iPhone/iPad](https://github.com/zoompilot/jetlink/blob/v0.8.12/docs/iphone-app.md)

For an existing native Jetson installation, pin the update explicitly:

```sh
jetlink update --ref v0.8.12
jetlink status
```

For a new server installation, use the pinned installer:

```sh
curl -fsSL https://raw.githubusercontent.com/zoompilot/jetlink/v0.8.12/install.sh -o install-v0.8.12.sh
bash install-v0.8.12.sh --ref v0.8.12
```

The current catalog is supplied by the pinned JetLink registry through the
model manager. It includes the corrected Mountain Dew Model and removes
Mountain Dew V2 Preview. Large model downloads and engine preparation happen
offroad. The archived Android 0.8.0 APK is not this release.

## Validation

The repository regression checks cover the adapter contract, disabled/missing
package behavior, USB ownership, provisioning, model selection, MADS handoff,
fallback history reset, and real tinygrad camera-to-inference plumbing. The new
warp format is compared byte for byte with this fork's existing camera graph.
The Clarity PTC/Honda CAN and safety tests are also retained.

Software tests do not establish a working device installation. After a separate
deployment, verify the client/server versions, selected model hash, a fresh
parked engine handshake, USB inference, and fallback before any vehicle testing.
