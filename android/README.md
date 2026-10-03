# JetLink Android APK

[Download jetlink-0.8.0-pixel.apk](https://github.com/ryanafdahl/Clarity-Pilot/raw/refs/heads/main/android/jetlink-0.8.0-pixel.apk)

This is the exact APK built and installed on the Pixel 11 Pro XL on October 3, 2026. It is the upstream JetLink app, not the earlier experimental Pixel benchmark app. It uses protocol v3 and matches this repository's JetLink client and the upgraded Jetson server.

| Field | Value |
| --- | --- |
| Version / code | `0.8.0` / `800` |
| Package | `io.zoompilot.jetlink.android` |
| Source | [zoompilot/jetlink at 9f3d318](https://github.com/zoompilot/jetlink/tree/9f3d3187758b810adc99b06cc0a1a19ab73b7acb) |
| Architecture | ARM64 |
| APK bytes | `103402267` |
| SHA-256 | `81a405c4ce26da7409f789445ac4fafe9f098c3b3cb9037374f06b6bfdf868f8` |
| Build tools | Swift 6.4.0 + matching Android SDK, Android platform 37, NDK 30.0.16248370, JDK 17, Ubuntu under WSL |
| Signing | Local debug key, as configured by upstream's release build; private key is not included |

## Install on the Pixel

Enable Developer options and USB debugging, connect to a computer with Android platform-tools, and authorize its debugging prompt. From the repository root:

```powershell
Get-FileHash .\android\jetlink-0.8.0-pixel.apk -Algorithm SHA256
adb devices
adb install -r .\android\jetlink-0.8.0-pixel.apk
adb shell am start -n io.zoompilot.jetlink.android/io.zoompilot.jetlink.MainActivity
```

Compare the hash above before installing. If several phones are connected, add `-s YOUR_DEVICE_SERIAL` after `adb`. Alternatively, download the APK onto the phone and allow the file manager to install it. Allow JetLink notifications so its foreground service can remain active.

An update must use the same signing key. A signature mismatch means it came from a different builder; do not uninstall automatically, because that removes app data and prepared models. Keep the original signing key privately for future builds.

On this Pixel, use **Settings → Processor → GPU** (LiteRT). QNN's NPU profiles target Qualcomm Snapdragon, not Google Tensor. In **Models**, choose **Cinque Terre Model V2** and tap **Get**; allow roughly 3 GB per prepared model. Model files are not bundled in this APK. V2 was verified on the comma and Jetson, but preparation on this Pixel has not yet been verified.

While parked, enable **Settings → Models → Accelerator Link** on the comma. Connect the Pixel through a USB 3 hub with USB-C power pass-through, then a USB-A-to-C data cable from the hub to the comma. Accept Android's USB permission prompt and check for **Connected over USB 3**. Choose either the Pixel or Jetson as the attached accelerator.

## Validation and rebuilding

The release build and all 51 Android unit tests passed. Installation, native library loading, and foreground server startup were verified on Pixel 11 Pro XL / Android 17. Model inference, direct comma USB operation, benchmark, and parity checks remain unverified for this APK.

Before driving, complete the pinned upstream guide's one-minute and ten-minute benchmarks while charging in the intended mount, output-parity check, and parked comma USB test. See the [Android user guide](https://github.com/zoompilot/jetlink/blob/9f3d3187758b810adc99b06cc0a1a19ab73b7acb/docs/android-app.md) and [build instructions](https://github.com/zoompilot/jetlink/blob/9f3d3187758b810adc99b06cc0a1a19ab73b7acb/android/README.md).

After installing the documented toolchains on Linux or macOS:

```sh
git clone https://github.com/zoompilot/jetlink.git
cd jetlink
git checkout 9f3d3187758b810adc99b06cc0a1a19ab73b7acb
cd android
./gradlew :app:assembleRelease :app:testDebugUnitTest
```

A rebuild is not guaranteed to have this APK's exact bytes or signature. JetLink's [MIT license](LICENSE-JetLink) is included. The APK also bundles LiteRT (Apache 2.0), ONNX Runtime (MIT), and Qualcomm QNN libraries under the Qualcomm AI Stack License; see upstream's [license notes](https://github.com/zoompilot/jetlink/blob/9f3d3187758b810adc99b06cc0a1a19ab73b7acb/android/README.md#licenses). QNN libraries are distributed inside the app, not separately.
