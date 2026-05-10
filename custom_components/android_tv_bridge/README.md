# Android TV Bridge

Public beta: this integration is usable, but the APIs and entity behaviour may still change while Android TV, Google TV, and Fire TV support is tested across more devices.

Android TV Bridge combines Android TV Remote and ADB access into one Home Assistant integration. It is intended for TVs and streaming boxes where source switching, app launching, power control, and media state need to work together.

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

The integration settings page allows you to adjust:

- **Polling interval**: how often the integration refreshes power, volume, app, source, and media state.
- **Hide apps from source selector**: discovered apps that should not appear as selectable sources.
- **Hide inputs and commands from source selector**: TV inputs, key commands, or other non-app sources that should not appear as selectable sources.

Hidden apps and sources are only removed from the selector. Detection aliases can still be used internally so states such as screensaver can be displayed without making them selectable.

## Power and ADB Behaviour

Some TVs expose ADB or Android TV Remote ports before Android TV services are fully awake. The integration waits briefly before heavier ADB discovery, retries source/app discovery during startup warm-up, and rebuilds the ADB client after transient timeout/offline failures.

When turning on through the integration, Android TV Bridge sends the power command and then a short delayed Home key. This helps app/source discovery populate on TVs that need a UI wake nudge after standby.

## Source Names

Physical TV inputs are shown with friendly names when the device exposes enough information. For example:

- `HDMI 1 - Game Console`
- `HDMI 2 - Set Top Box`
- `HDMI 3`
- `Composite`
- `Component`
- `VGA`

If the TV only exposes a label or only exposes a port, the integration uses the best friendly name available.

## Links

- Documentation: https://github.com/Hyperion5088/homeassistant-android-tv-bridge
- Issues: https://github.com/Hyperion5088/homeassistant-android-tv-bridge/issues
