"""Device profile helpers."""

from __future__ import annotations

import json
import re
from typing import Any

from .const import PROFILE_FIRE_TV, PROFILE_GENERIC, PROFILE_TCL_GOOGLE_TV
from .models import DiscoveredApp, MediaMetadata, PhysicalSource, Source, SourceKind

TCL_INPUT_LABEL_RE = re.compile(r"([^,]+),([^:]+)")
ACTIVE_INPUT_RE = re.compile(r"inputId:\s+([^\s]+)")
INPUT_ID_RE = re.compile(
    r"(?P<input_id>[\w.]+/[\w.$]+(?:/[\w.$]+)*(?:/HW\d+|/HDMI\d+)?)"
)
HDMI_PORT_RE = re.compile(r"(?:hdmi[_ ]?port|port)[=:]\s*(?P<port>\d+)", re.I)
HARDWARE_INFO_RE = re.compile(
    r"TvInputHardwareInfo\s+\{id=(?P<id>\d+),\s*type=(?P<type>\d+).*?\}",
    re.I,
)
HDMI_PORT_INFO_RE = re.compile(r"hdmi_port=(?P<port>\d+)", re.I)
HARDWARE_INPUT_MAP_RE = re.compile(
    r"(?P<hardware_id>\d+):\s+(?P<input_id>[\w.]+/[\w.$]+(?:/[\w.$]+)*)"
)
HDMI_CEC_DEVICE_RE = re.compile(
    r"CEC:.*?display_name:\s*(?P<label>.*?)\s+power_status:.*?port_id:\s*(?P<port>\d+)",
    re.I,
)
TV_INPUT_HARDWARE_TYPES = {
    1: "Other",
    2: "Tuner",
    3: "Composite",
    4: "S-Video",
    5: "SCART",
    6: "Component",
    7: "VGA",
    8: "DVI",
    9: "HDMI",
    10: "DisplayPort",
}
LABEL_PATTERNS = (
    re.compile(r"(?:custom[_ ]?label|label|name)[=:]\s*['\"]?(?P<label>[^,'\"\]\}]+)", re.I),
    re.compile(r"(?P<input_id>[\w.]+/[\w.$]+(?:/[\w.$]+)*(?:/HW\d+|/HDMI\d+)?)=(?P<label>[^,\]\}]+)"),
)
LAUNCHER_ACTIVITY_RE = re.compile(
    r"(?P<package>[a-zA-Z][\w]*(?:\.[\w]+)+)/(?P<activity>[^\s]+)"
)
PACKAGE_RE = re.compile(r"package:(?P<package>[a-zA-Z][\w]*(?:\.[\w]+)+)")
METADATA_FIELD_PATTERNS = {
    "title": (
        re.compile(r"(?:android\.media\.metadata\.TITLE|title)\s*[=:]\s*(?P<value>[^,\n\}]+)", re.I),
        re.compile(r'description="(?P<value>[^"]+)"', re.I),
    ),
    "artist": (
        re.compile(r"(?:android\.media\.metadata\.ARTIST|artist)\s*[=:]\s*(?P<value>[^,\n\}]+)", re.I),
    ),
    "album": (
        re.compile(r"(?:android\.media\.metadata\.ALBUM|album)\s*[=:]\s*(?P<value>[^,\n\}]+)", re.I),
    ),
    "image_url": (
        re.compile(r"(?:android\.media\.metadata\.ART_URI|artUri|iconUri|mediaUri)\s*[=:]\s*(?P<value>[^,\s\}\"]+)", re.I),
    ),
    "playback_state": (
        re.compile(r"state=PlaybackState\s*\{(?P<value>[^,\}]+)", re.I),
    ),
}
NOTIFICATION_FIELD_PATTERNS = {
    "title": (
        re.compile(r"android\.title=String\s+\((?P<value>[^\n]+?)\)", re.I),
        re.compile(r"tickerText=(?P<value>[^\n]+)", re.I),
    ),
    "artist": (
        re.compile(r"android\.text=String\s+\((?P<value>[^\n]+?)\)", re.I),
        re.compile(r"android\.subText=String\s+\((?P<value>[^\n]+?)\)", re.I),
    ),
    "album": (
        re.compile(r"android\.summaryText=String\s+\((?P<value>[^\n]+?)\)", re.I),
    ),
    "image_url": (
        re.compile(r"android\.largeIcon=Icon\s+\(Icon\(typ=URI uri=(?P<value>[^)\s]+)", re.I),
        re.compile(r"android\.picture=Icon\s+\(Icon\(typ=URI uri=(?P<value>[^)\s]+)", re.I),
    ),
}

PLAYBACK_STATE_NAMES = {
    "0": "idle",
    "1": "stopped",
    "2": "paused",
    "3": "playing",
    "4": "fast_forwarding",
    "5": "rewinding",
    "6": "buffering",
    "7": "error",
    "8": "connecting",
    "9": "skipping_to_previous",
    "10": "skipping_to_next",
    "11": "skipping_to_queue_item",
}

APP_NAMES = {
    "air.ITVMobilePlayer": "ITVX",
    "com.amazon.amazonvideo.livingroom": "Prime Video",
    "com.apple.atve.androidtv.appletv": "Apple TV",
    "com.disney.disneyplus": "Disney+",
    "com.google.android.youtube.tv": "YouTube",
    "com.google.android.youtube.tvmusic": "YouTube Music",
    "com.netflix.ninja": "Netflix",
    "com.plexapp.android": "Plex",
    "com.spotify.tv.android": "Spotify",
    "com.tcl.tv": "TV",
    "tv.wuaki.apptv": "Rakuten TV",
    "uk.co.bbc.iplayer": "BBC iPlayer",
    "uk.co.freeview.bbc": "BBC iPlayer",
    "uk.co.freeview.ch4_vod": "Channel 4",
    "uk.co.freeview.ch5": "Channel 5",
}

EXCLUDED_APP_PACKAGES = {
    "com.tcl.tv",
    "org.chromium.webview_shell",
    "uk.co.freeview.systemdistributor",
}


def default_sources(profile: str) -> list[dict[str, str]]:
    """Return sensible starter sources for a profile."""
    if profile == PROFILE_TCL_GOOGLE_TV:
        return []
    if profile == PROFILE_FIRE_TV:
        return [
            {
                "name": "Home",
                "type": SourceKind.KEY.value,
                "value": "HOME",
                "match": "com.amazon.tv.launcher",
            },
            {
                "name": "Plex",
                "type": SourceKind.APP.value,
                "value": "com.plexapp.android",
                "match": "com.plexapp.android",
            },
            {
                "name": "Netflix",
                "type": SourceKind.APP.value,
                "value": "com.netflix.ninja",
                "match": "com.netflix.ninja",
            },
        ]
    return []


def parse_sources(raw: str | list[dict[str, Any]]) -> list[Source]:
    """Parse source JSON from config data."""
    data = json.loads(raw) if isinstance(raw, str) else raw
    return [Source.from_dict(item) for item in data]


def source_map_json(profile: str) -> str:
    """Return pretty default source JSON."""
    return json.dumps(default_sources(profile), indent=2)


def parse_source_filter(raw: str | list[str] | None) -> list[str]:
    """Parse newline or comma separated source filter terms."""
    if raw is None:
        return []
    if isinstance(raw, str):
        values = re.split(r"[\n,]+", raw)
    else:
        values = raw
    return [
        value.strip().lower()
        for value in values
        if isinstance(value, str) and value.strip()
    ]


def source_matches_filter(source: Source, filters: list[str]) -> bool:
    """Return true when a source matches a configured filter term."""
    if not filters:
        return False

    haystacks = [
        source.name,
        source.value,
        source.match or "",
        source.kind.value,
    ]
    searchable = " ".join(value.lower() for value in haystacks if value)
    return any(term in searchable for term in filters)


def detect_source_name(
    sources: list[Source],
    *,
    current_app: str | None,
    hdmi_input: str | None,
) -> str | None:
    """Return the configured source name matching current raw state."""
    haystacks = [value for value in (hdmi_input, current_app) if value]
    for source in sources:
        if source.match and any(source.match in value for value in haystacks):
            return source.name
    return current_app or hdmi_input


def extract_active_tv_input(dumpsys_tv_input: str) -> str | None:
    """Extract the active TV input id from dumpsys tv_input."""
    matches = ACTIVE_INPUT_RE.findall(dumpsys_tv_input)
    return matches[-1] if matches else None


def extract_physical_sources(dumpsys_tv_input: str) -> list[PhysicalSource]:
    """Extract physical TV inputs from dumpsys tv_input output."""
    discovered: dict[str, PhysicalSource] = {}
    label_overrides = _extract_input_labels(dumpsys_tv_input)
    hardware_info = _extract_hardware_info(dumpsys_tv_input)
    cec_labels = _extract_hdmi_cec_labels(dumpsys_tv_input)
    input_ids = _extract_physical_input_ids(dumpsys_tv_input)

    for input_id in input_ids:
        label = label_overrides.get(input_id)
        info = _hardware_info_for_input(input_id, hardware_info)
        port = info.get("port") if info else None
        input_type = info.get("type") if info else None
        if label is None and port is not None:
            label = cec_labels.get(port)
        if input_type is None and not _looks_like_physical_input(input_id):
            continue

        existing = discovered.get(input_id)
        if existing and not label:
            if existing.port is not None or port is None:
                continue
            label = existing.label
        name = _physical_source_name(input_id, label, port, input_type)
        discovered[input_id] = PhysicalSource(
            name=name,
            input_id=input_id,
            uri=_physical_source_uri(input_id),
            port=port,
            label=label,
        )

    return sorted(
        discovered.values(),
        key=lambda source: (source.port is None, source.port or 999, source.name),
    )


def extract_discovered_apps(
    launcher_activities: str | None,
    installed_packages: list[str] | str | None,
) -> list[DiscoveredApp]:
    """Extract user-facing apps from launcher activity and package output."""
    packages: dict[str, str | None] = {}

    for line in (launcher_activities or "").splitlines():
        match = LAUNCHER_ACTIVITY_RE.search(line)
        if match:
            packages[match.group("package")] = match.group("activity")

    if isinstance(installed_packages, str):
        installed = [
            match.group("package")
            for match in PACKAGE_RE.finditer(installed_packages)
        ]
    else:
        installed = installed_packages or []

    for package in installed:
        if package in APP_NAMES and package not in packages:
            packages[package] = None

    apps = [
        DiscoveredApp(
            name=friendly_app_name(package),
            package=package,
            activity=activity,
        )
        for package, activity in packages.items()
        if _is_user_facing_app(package)
    ]
    return sorted(apps, key=lambda app: app.name.lower())


def is_selectable_app(package: str) -> bool:
    """Return true if an app package should be offered as a source option."""
    return package not in EXCLUDED_APP_PACKAGES


def extract_media_metadata(
    dumpsys_media_session: str,
    current_app: str | None,
) -> MediaMetadata | None:
    """Extract media metadata from dumpsys media_session."""
    session = _find_media_session(dumpsys_media_session, current_app)
    if not session:
        return None

    values = {
        field: _extract_metadata_field(session, patterns)
        for field, patterns in METADATA_FIELD_PATTERNS.items()
    }
    playback_state_raw = values["playback_state"]
    playback_state = _friendly_playback_state(playback_state_raw)
    if not any(values.values()):
        return MediaMetadata(raw_session=_trim_raw_session(session))

    return MediaMetadata(
        title=values["title"],
        artist=values["artist"],
        album=values["album"],
        image_url=values["image_url"],
        playback_state=playback_state,
        playback_state_raw=playback_state_raw,
        raw_session=_trim_raw_session(session),
    )


def extract_notification_media_metadata(
    dumpsys_notification: str,
    current_app: str | None,
) -> MediaMetadata | None:
    """Extract media metadata from Android notification output."""
    notification = _find_notification(dumpsys_notification, current_app)
    if not notification:
        return None

    values = {
        field: _extract_metadata_field(notification, patterns)
        for field, patterns in NOTIFICATION_FIELD_PATTERNS.items()
    }
    if not any(values.values()):
        return None

    return MediaMetadata(
        title=values["title"],
        artist=values["artist"],
        album=values["album"],
        image_url=values["image_url"],
        raw_session=_trim_raw_session(notification),
    )


def merge_media_metadata(
    primary: MediaMetadata | None,
    fallback: MediaMetadata | None,
) -> MediaMetadata | None:
    """Merge media metadata while keeping primary playback state."""
    if primary is None:
        return fallback
    if fallback is None:
        return primary

    return MediaMetadata(
        title=primary.title or fallback.title,
        artist=primary.artist or fallback.artist,
        album=primary.album or fallback.album,
        image_url=primary.image_url or fallback.image_url,
        playback_state=primary.playback_state or fallback.playback_state,
        playback_state_raw=primary.playback_state_raw or fallback.playback_state_raw,
        raw_session=primary.raw_session,
    )


def profile_supports_hdmi(profile: str) -> bool:
    """Return true if this profile has local TV input parsing support."""
    return profile in {PROFILE_TCL_GOOGLE_TV, PROFILE_FIRE_TV}


def _find_media_session(
    dumpsys_media_session: str,
    current_app: str | None,
) -> str | None:
    """Find the most relevant media session block."""
    if not dumpsys_media_session:
        return None

    chunks = re.split(r"\n\s*(?:Session|MediaSession)Record", dumpsys_media_session)
    if current_app:
        for chunk in chunks:
            if current_app in chunk:
                return chunk

    for chunk in chunks:
        if "PlaybackState" in chunk or "metadata" in chunk.lower():
            return chunk
    return dumpsys_media_session


def _find_notification(
    dumpsys_notification: str,
    current_app: str | None,
) -> str | None:
    """Find the most relevant notification block for the active app."""
    if not dumpsys_notification or not current_app:
        return None

    chunks = re.split(r"\n\s*NotificationRecord", dumpsys_notification)
    for chunk in chunks:
        if current_app not in chunk:
            continue
        if (
            "category=transport" in chunk
            or "android.mediaSession" in chunk
            or "android.title" in chunk
        ):
            return chunk
    return None


def _extract_metadata_field(
    session: str,
    patterns: tuple[re.Pattern[str], ...],
) -> str | None:
    """Extract one metadata field from a media session block."""
    for pattern in patterns:
        match = pattern.search(session)
        if not match:
            continue
        value = _clean_metadata_value(match.group("value"))
        if value:
            return value
    return None


def _clean_metadata_value(value: str) -> str | None:
    """Clean a metadata value captured from dumpsys output."""
    cleaned = value.strip().strip("'\"")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned or cleaned.lower() in {"null", "none", "<unknown>"}:
        return None
    return cleaned


def _friendly_playback_state(value: str | None) -> str | None:
    """Return a friendly playback state for Android PlaybackState values."""
    if value is None:
        return None
    match = re.search(r"(?:state=)?(?P<state>\d+)", value)
    if match:
        return PLAYBACK_STATE_NAMES.get(match.group("state"), value)
    return value


def _trim_raw_session(session: str) -> str:
    """Trim raw session data to keep state attributes manageable."""
    lines = [line.strip() for line in session.splitlines() if line.strip()]
    return "\n".join(lines[:20])


def _is_user_facing_app(package: str) -> bool:
    """Return true for apps worth showing in a source list."""
    if package in EXCLUDED_APP_PACKAGES:
        return False
    if package in APP_NAMES:
        return True
    blocked_prefixes = (
        "android.",
        "com.android.",
        "com.google.android.",
        "com.mediatek.",
        "com.tcl.",
    )
    allowed_google_tv = {
        "com.google.android.youtube.tv",
        "com.google.android.youtube.tvmusic",
    }
    if package in allowed_google_tv:
        return True
    return not package.startswith(blocked_prefixes)


def friendly_app_name(package: str) -> str:
    """Return a fallback friendly app name from a package id."""
    if package in APP_NAMES:
        return APP_NAMES[package]
    tail = package.rsplit(".", 1)[-1]
    replacements = {
        "ninja": "Netflix",
        "livingroom": "Prime Video",
        "android": package.rsplit(".", 2)[-2],
    }
    tail = replacements.get(tail, tail)
    return tail.replace("_", " ").replace("-", " ").title()


def _extract_input_labels(dumpsys_tv_input: str) -> dict[str, str]:
    """Extract custom labels keyed by input id."""
    labels: dict[str, str] = {}
    for pattern in LABEL_PATTERNS:
        for match in pattern.finditer(dumpsys_tv_input):
            input_id = match.groupdict().get("input_id")
            label = _clean_label(match.group("label"))
            if input_id and label:
                labels[input_id] = label
    return labels


def _extract_label(line: str) -> str | None:
    """Extract a source label from one dumpsys line."""
    for pattern in LABEL_PATTERNS:
        match = pattern.search(line)
        if not match:
            continue
        label = _clean_label(match.group("label"))
        if label:
            return label
    return None


def _extract_port(input_id: str, line: str) -> int | None:
    """Extract an HDMI port number when present."""
    match = HDMI_PORT_RE.search(line)
    if match:
        return int(match.group("port"))

    return None


def _looks_like_physical_input(input_id: str) -> bool:
    """Return true when an input id is a real physical TV HDMI source."""
    lower = input_id.lower()
    tail = input_id.rsplit("/", 1)[-1].lower()
    if not ("passthrough" in lower or "hdmi" in lower or re.fullmatch(r"hw\d+", tail)):
        return False
    return bool(re.fullmatch(r"hw\d+", tail) or re.fullmatch(r"hdmi[1-9]\d?", tail))


def _physical_source_name(
    input_id: str,
    label: str | None,
    port: int | None,
    input_type: int | None = None,
) -> str:
    """Return a friendly name for a physical input."""
    type_name = TV_INPUT_HARDWARE_TYPES.get(input_type or 0)
    if port is not None:
        source_name = f"HDMI {port}"
        if label:
            return f"{source_name} - {label}"
        return source_name
    if label:
        if type_name:
            return f"{type_name} - {label}"
        return label
    if type_name:
        return type_name
    return input_id.rsplit("/", 1)[-1]


def _physical_source_uri(input_id: str) -> str:
    """Return an Android TV passthrough content URI for an input id."""
    return f"content://android.media.tv/passthrough/{input_id.replace('/', '%2F')}"


def _clean_label(label: str) -> str | None:
    """Clean a label captured from dumpsys output."""
    cleaned = label.strip().strip("'\"")
    cleaned = re.split(
        r"\s+(?:hdmi[_ ]?port|port|input|state|type|hardware)[=:]",
        cleaned,
        maxsplit=1,
        flags=re.I,
    )[0].strip()
    if not cleaned or cleaned.lower() in {"null", "none"}:
        return None
    return cleaned


def _extract_hardware_info(dumpsys_tv_input: str) -> dict[str, dict[str, int | None]]:
    """Extract TV input hardware type and port metadata."""
    hardware: dict[str, dict[str, int | None]] = {}
    for match in HARDWARE_INFO_RE.finditer(dumpsys_tv_input):
        raw = match.group(0)
        port_match = HDMI_PORT_INFO_RE.search(raw)
        hardware[match.group("id")] = {
            "type": int(match.group("type")),
            "port": int(port_match.group("port")) if port_match else None,
        }
    return hardware


def _extract_hdmi_cec_labels(dumpsys_tv_input: str) -> dict[int, str]:
    """Extract HDMI CEC display names keyed by HDMI port."""
    labels: dict[int, str] = {}
    for match in HDMI_CEC_DEVICE_RE.finditer(dumpsys_tv_input):
        label = _clean_label(match.group("label"))
        if label:
            labels[int(match.group("port"))] = label
    return labels


def _extract_physical_input_ids(dumpsys_tv_input: str) -> list[str]:
    """Extract selectable physical TV input IDs."""
    input_ids: dict[str, None] = {}
    for line in dumpsys_tv_input.splitlines():
        match = INPUT_ID_RE.search(line)
        if match and _looks_like_physical_input(match.group("input_id")):
            input_ids[match.group("input_id")] = None

        map_match = HARDWARE_INPUT_MAP_RE.search(line)
        if map_match:
            input_ids[map_match.group("input_id")] = None
    return list(input_ids)


def _hardware_info_for_input(
    input_id: str,
    hardware_info: dict[str, dict[str, int | None]],
) -> dict[str, int | None] | None:
    """Return hardware info for a physical input ID."""
    match = re.search(r"(?:HW|HDMI)(?P<hardware_id>\d+)$", input_id)
    if match and match.group("hardware_id") in hardware_info:
        return hardware_info[match.group("hardware_id")]
    return None
