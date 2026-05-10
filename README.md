# Android TV Bridge

> Public beta: this integration is usable, but the APIs and entity behaviour may still change while Android TV, Google TV, and Fire TV support is tested across more devices.

Android TV Bridge is a Home Assistant custom integration for Android TV, Google TV, and Fire TV devices. It combines Android TV Remote and ADB control so one media player can expose power, source selection, app launching, volume, and media state.

## Features

- Android TV Remote power and key commands.
- ADB app launching and HDMI/input switching.
- Friendly source names such as `HDMI 1 - Game Console`.
- Local inputs and commands listed before apps in source selectors.
- Configurable polling interval.
- Separate settings filters for hiding discovered apps and local sources.
- Media metadata sensors where Android exposes usable metadata.
- Startup ADB warm-up/retry handling for TVs that are slow to expose app or source data.
- Post-power-on wake nudge to help Android TV UI and ADB reporting settle after standby.

## HACS Installation

This repository is intended to be installable as a HACS custom repository.

1. Open HACS in Home Assistant.
2. Add this repository as a custom repository.
3. Select category **Integration**.
4. Install **Android TV Bridge**.
5. Restart Home Assistant.
6. Add the integration from **Settings** > **Devices & services**.

## Public Beta Notes

- Source naming and metadata support vary by device and app.
- Android TV, Google TV, and Fire TV devices can expose different ADB and Android TV Remote behaviour after standby.
- Please use GitHub issues for bugs and feature requests, with device type, Home Assistant version, and relevant sanitized logs.

## Before Adding a Device

Give the TV or streaming box a static IP address or DHCP reservation before adding it to Home Assistant.

## Enable Developer Mode and ADB

### Google TV / Android TV

1. Open **Settings** on the TV.
2. Go to **System** > **About**.
3. Select **Android TV OS build** repeatedly until developer mode is enabled.
4. Go back to **System** > **Developer options**.
5. Turn on **USB debugging** or **Network debugging**, depending on what the device offers.
6. When Home Assistant connects for the first time, accept the ADB authorisation prompt on the TV.

Some TVs hide developer options under **Device preferences** > **About** rather than **System** > **About**.

### Amazon Fire TV

1. Open **Settings**.
2. Go to **My Fire TV** > **About**.
3. Select the device name repeatedly until developer mode is enabled.
4. Go back to **My Fire TV** > **Developer Options**.
5. Turn on **ADB Debugging**.
6. When Home Assistant connects for the first time, accept the ADB authorisation prompt on the TV.

## Settings

- **Polling interval**: how often the integration refreshes power, volume, app, source, and media state.
- **Hide apps from source selector**: discovered apps that should not appear as selectable sources.
- **Hide inputs and commands from source selector**: TV inputs, key commands, or other non-app sources that should not appear as selectable sources.

Hidden apps and sources are only removed from the selector. Detection aliases can still be used internally so states such as screensaver can be displayed without making them selectable.

## Power and ADB Behaviour

Some TVs expose their network ports before Android TV services are fully awake. Android TV Bridge delays heavier ADB discovery briefly after startup, retries missing source/app discovery during a warm-up window, and rebuilds the ADB client after transient timeout/offline failures.

When turning on through the integration, Android TV Bridge sends the power command and then a short delayed Home key. This mirrors the manual wake action often needed for Android TV UI, app, and source reporting to become available after deeper standby.

## Branding

The integration ships local Home Assistant brand assets in `custom_components/android_tv_bridge/brand/`.

If this integration later moves into Home Assistant Core, the local brand assets should be removed and submitted to the Home Assistant brands repository instead.

## License

Android TV Bridge is released under the MIT License.

Runtime dependencies:

- `androidtv` under the MIT License.
- `androidtvremote2` under the Apache License 2.0.
