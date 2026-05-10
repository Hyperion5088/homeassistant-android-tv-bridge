"""Data models for Android TV Bridge."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class SourceKind(StrEnum):
    """Supported source action types."""

    ADB_INTENT = "adb_intent"
    APP = "app"
    KEY = "key"


@dataclass(frozen=True)
class Source:
    """A source shown in Home Assistant."""

    name: str
    kind: SourceKind
    value: str
    match: str | None = None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Source":
        """Build a source from config flow JSON."""
        return cls(
            name=str(raw["name"]),
            kind=SourceKind(raw["type"]),
            value=str(raw["value"]),
            match=str(raw.get("match") or raw["value"]),
        )


@dataclass(frozen=True)
class PhysicalSource:
    """A physical TV input discovered from the device."""

    name: str
    input_id: str
    uri: str
    port: int | None = None
    label: str | None = None

    def as_source(self) -> Source:
        """Return this physical input as a selectable source."""
        return Source(
            name=self.name,
            kind=SourceKind.ADB_INTENT,
            value=self.uri,
            match=self.input_id,
        )

    def as_dict(self) -> dict[str, Any]:
        """Return a serializable representation."""
        return {
            "name": self.name,
            "input_id": self.input_id,
            "uri": self.uri,
            "port": self.port,
            "label": self.label,
        }


@dataclass(frozen=True)
class DiscoveredApp:
    """An app discovered on the Android TV device."""

    name: str
    package: str
    activity: str | None = None

    def as_source(self) -> Source:
        """Return this app as a selectable source."""
        return Source(
            name=self.name,
            kind=SourceKind.APP,
            value=self.package,
            match=self.package,
        )

    def as_dict(self) -> dict[str, Any]:
        """Return a serializable representation."""
        return {
            "name": self.name,
            "package": self.package,
            "activity": self.activity,
        }


@dataclass(frozen=True)
class MediaMetadata:
    """Media metadata discovered from Android media sessions."""

    title: str | None = None
    artist: str | None = None
    album: str | None = None
    image_url: str | None = None
    playback_state: str | None = None
    playback_state_raw: str | None = None
    raw_session: str | None = None

    def as_dict(self) -> dict[str, str | None]:
        """Return a serializable representation."""
        return {
            "title": self.title,
            "artist": self.artist,
            "album": self.album,
            "image_url": self.image_url,
            "playback_state": self.playback_state,
            "playback_state_raw": self.playback_state_raw,
            "raw_session": self.raw_session,
        }


@dataclass
class BridgeState:
    """Current bridge state."""

    available: bool = False
    power_on: bool | None = None
    current_app: str | None = None
    current_source: str | None = None
    raw_hdmi_input: str | None = None
    physical_sources: list[dict[str, Any]] | None = None
    apps: list[dict[str, Any]] | None = None
    media_title: str | None = None
    media_artist: str | None = None
    media_album: str | None = None
    media_image_url: str | None = None
    media_playback_state: str | None = None
    media_playback_state_raw: str | None = None
    volume_level: float | None = None
    muted: bool | None = None
    device_info: dict[str, Any] | None = None
    raw: dict[str, Any] | None = None
