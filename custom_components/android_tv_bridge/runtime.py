"""Runtime bridge for Android TV Bridge."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path
import time
from typing import Any

import androidtv
from androidtv.exceptions import LockNotAcquiredException
from androidtvremote2 import (
    AndroidTVRemote,
    CannotConnect,
    ConnectionClosed,
    InvalidAuth,
)

from homeassistant.core import HomeAssistant

from .const import (
    CONF_ADB_KEY_PATH,
    CONF_ADB_PORT,
    CONF_DEVICE_CLASS,
    CONF_ENABLE_REMOTE_PROTOCOL,
    CONF_HIDDEN_APPS,
    CONF_HIDDEN_SOURCES,
    CONF_HOST,
    CONF_PROFILE,
    CONF_REMOTE_CERT_PATH,
    CONF_REMOTE_KEY_PATH,
    CONF_SOURCE_FILTER,
    DEFAULT_ADB_PORT,
    DEFAULT_REMOTE_PORT,
    PROFILE_TCL_GOOGLE_TV,
)
from .models import (
    BridgeState,
    DiscoveredApp,
    MediaMetadata,
    PhysicalSource,
    Source,
    SourceKind,
)
from .profiles import (
    default_sources,
    detect_source_name,
    extract_active_tv_input,
    extract_discovered_apps,
    extract_media_metadata,
    extract_notification_media_metadata,
    extract_physical_sources,
    is_selectable_app,
    merge_media_metadata,
    parse_source_filter,
    parse_sources,
    profile_supports_hdmi,
    source_matches_filter,
)

SCREEN_SAVER_APPS = {
    "com.google.android.backdrop": "Screensaver",
}
HOME_APPS = {
    "com.amazon.tv.launcher": "Home",
    "com.google.android.apps.tv.launcherx": "Home",
    "com.google.android.tvlauncher": "Home",
}
WAKE_FROM_SCREEN_SAVER_KEY = "BACK"
POST_POWER_ON_WAKE_KEY = "HOME"
POST_POWER_ON_WAKE_DELAY = 2
STARTUP_DISCOVERY_DELAY = 20
STARTUP_DISCOVERY_RETRY_WINDOW = 180
ADB_RECONNECT_COOLDOWN = 10


class AndroidTvBridgeRuntime:
    """Combined ADB and Android TV Remote runtime."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        data: dict[str, Any],
        sources: list[Source],
    ) -> None:
        """Initialize the runtime."""
        self.hass = hass
        self.entry_id = entry_id
        self.host = data[CONF_HOST]
        self.name = data.get("name", self.host)
        self.profile = data.get(CONF_PROFILE, PROFILE_TCL_GOOGLE_TV)
        self.device_class = data.get(CONF_DEVICE_CLASS, "auto")
        self.adb_port = data.get(CONF_ADB_PORT, DEFAULT_ADB_PORT)
        self.adb_key_path = data.get(CONF_ADB_KEY_PATH) or hass.config.path(
            ".storage/androidtv_adbkey"
        )
        self.enable_remote_protocol = data.get(CONF_ENABLE_REMOTE_PROTOCOL, True)
        self.remote_cert_path = data.get(CONF_REMOTE_CERT_PATH) or hass.config.path(
            ".storage/androidtv_remote_cert.pem"
        )
        self.remote_key_path = data.get(CONF_REMOTE_KEY_PATH) or hass.config.path(
            ".storage/androidtv_remote_key.pem"
        )
        self.sources = sources or parse_sources(default_sources(self.profile))
        self.source_filters = parse_source_filter(data.get(CONF_SOURCE_FILTER, ""))
        self.hidden_apps = set(data.get(CONF_HIDDEN_APPS, []))
        self.hidden_sources = set(data.get(CONF_HIDDEN_SOURCES, []))
        self.physical_sources: list[PhysicalSource] = []
        self.discovered_apps: list[DiscoveredApp] = []
        self._last_app_discovery = 0.0
        self._initial_update_complete = False
        self._started_at = time.monotonic()
        self._last_adb_reconnect = 0.0
        self.state = BridgeState()

        self._adb: Any | None = None
        self._remote: AndroidTVRemote | None = None
        self._remote_lock = asyncio.Lock()

    async def async_setup(self) -> None:
        """Set up protocol clients."""
        await self.hass.async_add_executor_job(self._setup_adb)
        if self.enable_remote_protocol:
            await self._setup_remote()

    async def async_close(self) -> None:
        """Close protocol clients."""
        if self._remote:
            self._remote.disconnect()
            self._remote = None
        if self._adb:
            await self.hass.async_add_executor_job(self._adb.adb_close)
            self._adb = None

    async def async_update(self) -> BridgeState:
        """Update and return current state."""
        adb_state = await self.hass.async_add_executor_job(self._read_adb_state)
        remote_state = await self._read_remote_state()

        current_app = adb_state.get("current_app") or remote_state.get("current_app")
        hdmi_input = adb_state.get("hdmi_input")
        physical_sources = adb_state.get("physical_sources")
        discovered_apps = adb_state.get("apps")
        media_metadata = adb_state.get("media_metadata")
        if physical_sources:
            self.physical_sources = physical_sources
        if discovered_apps:
            self.discovered_apps = discovered_apps
        power_on = remote_state.get("power_on") or adb_state.get("power_on")
        if power_on is False:
            media_metadata = None
        current_source = detect_source_name(
            self.detection_sources(),
            current_app=current_app,
            hdmi_input=hdmi_input,
        )

        self.state = BridgeState(
            available=adb_state.get("available", False)
            or remote_state.get("available", False),
            power_on=power_on,
            current_app=current_app,
            current_source=current_source,
            raw_hdmi_input=hdmi_input,
            physical_sources=[source.as_dict() for source in self.physical_sources],
            apps=[app.as_dict() for app in self.discovered_apps],
            media_title=media_metadata.title if media_metadata else None,
            media_artist=media_metadata.artist if media_metadata else None,
            media_album=media_metadata.album if media_metadata else None,
            media_image_url=media_metadata.image_url if media_metadata else None,
            media_playback_state=media_metadata.playback_state if media_metadata else None,
            media_playback_state_raw=(
                media_metadata.playback_state_raw if media_metadata else None
            ),
            volume_level=remote_state.get("volume_level") or adb_state.get("volume_level"),
            muted=remote_state.get("muted") or adb_state.get("muted"),
            device_info=remote_state.get("device_info") or adb_state.get("device_info"),
            raw={"adb": adb_state, "remote": remote_state},
        )
        return self.state

    async def async_select_source(self, source_name: str) -> None:
        """Select a configured source."""
        source = next(
            (item for item in self.available_sources() if item.name == source_name),
            None,
        )
        if source is None:
            raise ValueError(f"Unknown source: {source_name}")

        await self.async_wake_from_screensaver()

        if source.kind is SourceKind.ADB_INTENT:
            await self.async_adb_command(
                f"am start -a android.intent.action.VIEW -d '{source.value}'"
            )
            return
        if source.kind is SourceKind.APP:
            await self.async_launch_app(source.value)
            return
        if source.kind is SourceKind.KEY:
            await self.async_send_key(source.value)
            return
        raise ValueError(f"Unsupported source type: {source.kind}")

    async def async_send_key(self, key: str) -> None:
        """Send a remote key."""
        if self._remote:
            async with self._remote_lock:
                self._remote.send_key_command(key)
            return
        await self.async_adb_command(f"input keyevent KEYCODE_{key}")

    async def async_launch_app(self, package: str) -> None:
        """Launch an app package."""
        await self.async_wake_from_screensaver()

        if self._adb:
            for category in (
                "android.intent.category.LEANBACK_LAUNCHER",
                "android.intent.category.LAUNCHER",
            ):
                result = await self.async_adb_command(
                    f"monkey -p {package} -c {category} 1"
                )
                if not _adb_launch_failed(result):
                    return

        if self._remote:
            async with self._remote_lock:
                self._remote.send_launch_app_command(f"android-app://{package}")
            return

        await self.hass.async_add_executor_job(self._adb.launch_app, package)

    async def async_wake_from_screensaver(self) -> None:
        """Wake the TV from Android TV screensaver/ambient mode."""
        if self.state.current_app not in SCREEN_SAVER_APPS:
            return
        await self.async_send_key(WAKE_FROM_SCREEN_SAVER_KEY)
        await asyncio.sleep(1)

    async def async_turn_on(self) -> None:
        """Turn on the device."""
        if self._remote:
            await self._remote_power(True, force=True)
            await asyncio.sleep(POST_POWER_ON_WAKE_DELAY)
            await self.async_send_key(POST_POWER_ON_WAKE_KEY)
            return
        await self.hass.async_add_executor_job(self._adb.turn_on)
        await asyncio.sleep(POST_POWER_ON_WAKE_DELAY)
        await self.async_send_key(POST_POWER_ON_WAKE_KEY)

    async def async_turn_off(self) -> None:
        """Turn off the device."""
        if self._remote:
            await self._remote_power(False)
            return
        await self.hass.async_add_executor_job(self._adb.turn_off)

    async def async_adb_command(self, command: str) -> str | None:
        """Run an ADB shell command."""
        return await self.hass.async_add_executor_job(
            self._adb_shell_with_retry,
            command,
        )

    def source_names(self) -> list[str]:
        """Return source names."""
        return [source.name for source in self.available_sources()]

    def available_sources(self) -> list[Source]:
        """Return configured sources plus discovered physical inputs."""
        sources = [
            self._format_source(source)
            for source in self.sources
            if source.kind is not SourceKind.APP or is_selectable_app(source.value)
        ]
        sources = self._filter_sources(sources)
        known_matches = {source.match for source in sources if source.match}
        known_values = {source.value for source in sources}
        known_names = {source.name for source in sources}

        for physical_source in self.physical_sources:
            source = physical_source.as_source()
            if self._is_filtered_source(source):
                continue
            if (
                source.match in known_matches
                or source.value in known_values
                or source.name in known_names
            ):
                continue
            sources.append(source)

        known_matches.update(source.match for source in sources if source.match)
        known_values.update(source.value for source in sources)
        known_names.update(source.name for source in sources)

        for discovered_app in self.discovered_apps:
            source = discovered_app.as_source()
            if self._is_filtered_source(source):
                continue
            if (
                source.match in known_matches
                or source.value in known_values
                or source.name in known_names
            ):
                continue
            sources.append(source)

        return _sort_sources_for_selector(sources)

    def detection_sources(self) -> list[Source]:
        """Return selector sources plus hidden/non-selectable detection aliases."""
        sources = list(self.available_sources())
        known_matches = {source.match for source in sources if source.match}
        known_values = {source.value for source in sources}
        known_names = {source.name for source in sources}

        for source in self.sources:
            formatted_source = self._format_source(source)
            if (
                formatted_source.match in known_matches
                or formatted_source.value in known_values
                or formatted_source.name in known_names
            ):
                continue
            sources.append(formatted_source)
            if formatted_source.match:
                known_matches.add(formatted_source.match)
            known_values.add(formatted_source.value)
            known_names.add(formatted_source.name)

        for discovered_app in self.discovered_apps:
            source = discovered_app.as_source()
            if (
                source.match in known_matches
                or source.value in known_values
                or source.name in known_names
            ):
                continue
            sources.append(source)
            if source.match:
                known_matches.add(source.match)
            known_values.add(source.value)
            known_names.add(source.name)

        for package, name in {**HOME_APPS, **SCREEN_SAVER_APPS}.items():
            if package in known_matches or package in known_values or name in known_names:
                continue
            sources.append(
                Source(
                    name=name,
                    kind=SourceKind.APP,
                    value=package,
                    match=package,
                )
            )
        return sources

    def _filter_sources(self, sources: list[Source]) -> list[Source]:
        """Remove sources hidden by the configured filter."""
        return [source for source in sources if not self._is_filtered_source(source)]

    def _is_filtered_source(self, source: Source) -> bool:
        """Return true when a source should be hidden from selection."""
        if source.kind is SourceKind.APP and _source_matches_values(
            source,
            self.hidden_apps,
        ):
            return True
        if source.kind is not SourceKind.APP and _source_matches_values(
            source,
            self.hidden_sources,
        ):
            return True
        return source_matches_filter(source, self.source_filters)

    def app_filter_options(self) -> list[dict[str, str]]:
        """Return app choices for the options flow hidden-app filter."""
        options: dict[str, str] = {}
        for source in self.sources:
            if source.kind is SourceKind.APP:
                options[source.value] = _source_option_label(source)
        for app in self.discovered_apps:
            source = app.as_source()
            options[source.value] = _source_option_label(source)
        return [
            {"value": value, "label": label}
            for value, label in sorted(options.items(), key=lambda item: item[1].lower())
        ]

    def source_filter_options(self) -> list[dict[str, str]]:
        """Return non-app source choices for the options flow hidden-source filter."""
        options: dict[str, str] = {}
        for source in self.sources:
            if source.kind is not SourceKind.APP:
                formatted_source = self._format_source(source)
                options[formatted_source.value] = _source_filter_option_label(
                    formatted_source
                )
        for physical_source in self.physical_sources:
            source = physical_source.as_source()
            options[source.value] = _source_filter_option_label(source)
        return [
            {"value": value, "label": label}
            for value, label in sorted(options.items(), key=lambda item: item[1].lower())
        ]

    def _format_source(self, source: Source) -> Source:
        """Format a configured source with richer discovered display details."""
        if source.kind is not SourceKind.ADB_INTENT:
            return source

        physical_source = self._matching_physical_source(source)
        if physical_source is None:
            return source

        name = _merged_physical_source_name(physical_source.name, source.name)
        if name == source.name:
            return source
        return Source(
            name=name,
            kind=source.kind,
            value=source.value,
            match=source.match,
        )

    def _matching_physical_source(self, source: Source) -> PhysicalSource | None:
        """Return the discovered physical input matching a configured source."""
        haystacks = [value for value in (source.match, source.value) if value]
        for physical_source in self.physical_sources:
            if any(value in physical_source.input_id for value in haystacks):
                return physical_source
            if any(physical_source.input_id in value for value in haystacks):
                return physical_source
        return None

    def _setup_adb(self) -> None:
        """Set up the ADB client."""
        self._adb = androidtv.setup(
            self.host,
            port=self.adb_port,
            adbkey=self.adb_key_path,
            device_class=self.device_class,
            auth_timeout_s=15,
            transport_timeout_s=5,
        )

    def _reconnect_adb_if_due(self) -> None:
        """Rebuild the ADB client after transient connection failures."""
        now = time.monotonic()
        if now - self._last_adb_reconnect < ADB_RECONNECT_COOLDOWN:
            return
        self._last_adb_reconnect = now
        if self._adb is not None:
            try:
                self._adb.adb_close()
            except Exception:  # noqa: BLE001
                pass
        self._setup_adb()

    async def _setup_remote(self) -> None:
        """Set up the Android TV Remote client."""
        Path(self.remote_cert_path).parent.mkdir(parents=True, exist_ok=True)
        self._remote = AndroidTVRemote(
            client_name="Home Assistant Android TV Bridge",
            certfile=self.remote_cert_path,
            keyfile=self.remote_key_path,
            host=self.host,
            api_port=DEFAULT_REMOTE_PORT,
            enable_ime=True,
        )
        await self._remote.async_generate_cert_if_missing()
        try:
            await self._remote.async_connect()
        except (CannotConnect, ConnectionClosed, InvalidAuth):
            self._remote = None

    def _read_adb_state(self) -> dict[str, Any]:
        """Read state from ADB."""
        if self._adb is None:
            return {"available": False}

        data: dict[str, Any] = {"available": False}
        try:
            props = self._adb.get_properties_dict(get_running_apps=False, lazy=True)
            data["available"] = True
            data["power_on"] = props.get("screen_on")
            data["current_app"] = props.get("current_app")
            data["muted"] = props.get("muted")
            data["volume_level"] = _normalise_volume(props.get("volume_level"))
            data["device_info"] = {
                "manufacturer": props.get("manufacturer"),
                "model": props.get("model"),
                "serialno": props.get("serialno"),
            }
        except Exception as err:  # noqa: BLE001
            data["error"] = str(err)
            self._reconnect_adb_if_due()

        should_run_discovery = data.get("available") and self._should_run_discovery()
        should_read_metadata = data.get("available") and self._startup_delay_elapsed()
        should_read_tv_input = (
            data.get("available")
            and self._startup_delay_elapsed()
            and profile_supports_hdmi(self.profile)
        )
        if should_run_discovery:
            try:
                data["apps"] = self._discover_apps()
            except Exception as err:  # noqa: BLE001
                data["apps_error"] = str(err)
                self._reconnect_adb_if_due()

        if should_read_metadata:
            try:
                data["media_metadata"] = self._read_media_metadata(
                    data.get("current_app")
                )
            except Exception as err:  # noqa: BLE001
                data["media_metadata_error"] = str(err)
                self._reconnect_adb_if_due()

        if should_read_tv_input:
            try:
                dumpsys = self._adb_shell_with_retry("dumpsys tv_input")
                data["hdmi_input"] = extract_active_tv_input(dumpsys or "")
                physical_sources = extract_physical_sources(dumpsys or "")
                if physical_sources:
                    data["physical_sources"] = physical_sources
            except Exception as err:  # noqa: BLE001
                data["hdmi_error"] = str(err)
                self._reconnect_adb_if_due()

        self._initial_update_complete = True
        return data

    def _startup_delay_elapsed(self) -> bool:
        """Return true after the startup ADB settling delay."""
        return (
            self._initial_update_complete
            and time.monotonic() - self._started_at >= STARTUP_DISCOVERY_DELAY
        )

    def _should_run_discovery(self) -> bool:
        """Return true when heavier ADB discovery should run."""
        if not self._startup_delay_elapsed():
            return False
        uptime = time.monotonic() - self._started_at
        if uptime < STARTUP_DISCOVERY_RETRY_WINDOW:
            return True
        if profile_supports_hdmi(self.profile) and not self.physical_sources:
            return True
        if not self.discovered_apps:
            return True
        return self.discovered_apps and time.monotonic() - self._last_app_discovery >= 1800

    def _discover_apps(self) -> list[DiscoveredApp]:
        """Discover launchable apps and cache them briefly."""
        now = time.monotonic()
        if self.discovered_apps and now - self._last_app_discovery < 1800:
            return self.discovered_apps

        try:
            launcher_activities = "\n".join(
                value
                for value in (
                    self._adb_shell_with_retry(
                        "cmd package query-activities --brief "
                        "-a android.intent.action.MAIN "
                        "-c android.intent.category.LEANBACK_LAUNCHER"
                    ),
                    self._adb_shell_with_retry(
                        "cmd package query-activities --brief "
                        "-a android.intent.action.MAIN "
                        "-c android.intent.category.LAUNCHER"
                    ),
                )
                if value
            )
        except Exception:  # noqa: BLE001
            launcher_activities = None
        try:
            installed_packages = self._adb.get_installed_apps()
        except Exception:  # noqa: BLE001
            installed_packages = None

        apps = extract_discovered_apps(launcher_activities, installed_packages)
        if apps:
            self._last_app_discovery = now
            self.discovered_apps = apps
        return apps

    def _read_media_metadata(self, current_app: str | None) -> MediaMetadata | None:
        """Read media metadata from Android media sessions and notifications."""
        media_session = self._adb_shell_with_retry("dumpsys media_session")
        metadata = extract_media_metadata(media_session or "", current_app)

        notification = self._adb_shell_with_retry("dumpsys notification --noredact")
        notification_metadata = extract_notification_media_metadata(
            notification or "",
            current_app,
        )
        return merge_media_metadata(metadata, notification_metadata)

    def _adb_shell_with_retry(self, command: str) -> str | None:
        """Run an ADB shell command, retrying transient library lock failures."""
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                return self._adb.adb_shell(command)
            except LockNotAcquiredException as err:
                last_error = err
                if attempt < 2:
                    time.sleep(0.35)
                    continue
                raise
            except Exception as err:  # noqa: BLE001
                last_error = err
                if attempt < 2:
                    self._reconnect_adb_if_due()
                    time.sleep(0.5)
                    continue
                raise
        if last_error:
            raise last_error
        return None

    async def _read_remote_state(self) -> dict[str, Any]:
        """Read state from Android TV Remote."""
        if self._remote is None:
            return {"available": False}
        return {
            "available": True,
            "power_on": self._remote.is_on,
            "current_app": self._remote.current_app,
            "volume_level": _normalise_remote_volume(self._remote.volume_info),
            "muted": (self._remote.volume_info or {}).get("muted"),
            "device_info": self._remote.device_info,
        }

    async def _remote_power(self, turn_on: bool, force: bool = False) -> None:
        """Turn the TV on or off using the remote protocol."""
        if not self._remote:
            return
        current = self._remote.is_on
        if current is turn_on and not force:
            return
        async with self._remote_lock:
            self._remote.send_key_command("POWER")


def _normalise_volume(value: Any) -> float | None:
    """Normalize ADB volume values."""
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number > 1:
        return number / 100
    return number


def _normalise_remote_volume(value: dict[str, Any] | None) -> float | None:
    """Normalize Android TV Remote volume values."""
    if not value:
        return None
    level = value.get("level")
    max_level = value.get("max") or 100
    try:
        return float(level) / float(max_level)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _source_matches_values(source: Source, values: set[str]) -> bool:
    """Return true when a source exactly matches one of the hidden values."""
    if not values:
        return False
    candidates = {source.name, source.value, source.match or ""}
    return bool(candidates & values)


def _source_option_label(source: Source) -> str:
    """Return a readable option label with enough detail to distinguish entries."""
    return source.name


def _source_filter_option_label(source: Source) -> str:
    """Return a readable physical source label for filter options."""
    return source.name


def _sort_sources_for_selector(sources: list[Source]) -> list[Source]:
    """Return local inputs/commands first, then apps."""
    return sorted(
        sources,
        key=lambda source: (
            source.kind is SourceKind.APP,
            source.name.lower(),
            source.value.lower(),
        ),
    )


def _merged_physical_source_name(physical_name: str, configured_name: str) -> str:
    """Merge discovered input names with configured friendly names."""
    if not configured_name or configured_name == physical_name:
        return physical_name
    if " - " in physical_name:
        return physical_name
    if configured_name.startswith(physical_name):
        return configured_name
    return f"{physical_name} - {configured_name}"


def _adb_launch_failed(result: str | None) -> bool:
    """Return true when monkey reports that it could not launch an app."""
    if result is None:
        return False
    lowered = result.lower()
    return "no activities found" in lowered or "monkey aborted" in lowered
