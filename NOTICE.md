# Notices

Android TV Bridge is distributed under the MIT License.

## Runtime Dependencies

- `androidtv` is used for ADB communication with Android TV and Fire TV devices. It is distributed under the MIT License.
- `androidtvremote2` is used for the Android TV Remote protocol. It is distributed under the Apache License 2.0.

This repository does not vendor those dependencies. They are installed by Home Assistant from the versions declared in `custom_components/android_tv_bridge/manifest.json`.
