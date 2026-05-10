"""Media player platform for Android TV Bridge."""

from __future__ import annotations

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import AndroidTvBridgeCoordinator
from .entity import AndroidTvBridgeEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up media player entities."""
    coordinator: AndroidTvBridgeCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([AndroidTvBridgeMediaPlayer(coordinator)])


class AndroidTvBridgeMediaPlayer(AndroidTvBridgeEntity, MediaPlayerEntity):
    """Combined media player for a bridge device."""

    _attr_name = None
    _attr_supported_features = (
        MediaPlayerEntityFeature.TURN_ON
        | MediaPlayerEntityFeature.TURN_OFF
        | MediaPlayerEntityFeature.SELECT_SOURCE
        | MediaPlayerEntityFeature.VOLUME_SET
    )

    def __init__(self, coordinator: AndroidTvBridgeCoordinator) -> None:
        """Initialize the media player."""
        super().__init__(coordinator, "media_player")

    @property
    def available(self) -> bool:
        """Return availability."""
        return bool(self.coordinator.data and self.coordinator.data.available)

    @property
    def state(self) -> MediaPlayerState:
        """Return media player state."""
        if self.coordinator.data and self.coordinator.data.power_on:
            return MediaPlayerState.ON
        return MediaPlayerState.OFF

    @property
    def source(self) -> str | None:
        """Return current source."""
        return self.coordinator.data.current_source if self.coordinator.data else None

    @property
    def source_list(self) -> list[str]:
        """Return source list."""
        return self.coordinator.runtime.source_names()

    @property
    def volume_level(self) -> float | None:
        """Return volume level."""
        return self.coordinator.data.volume_level if self.coordinator.data else None

    @property
    def is_volume_muted(self) -> bool | None:
        """Return mute state."""
        return self.coordinator.data.muted if self.coordinator.data else None

    @property
    def media_title(self) -> str | None:
        """Return current media title."""
        return self.coordinator.data.media_title if self.coordinator.data else None

    @property
    def media_artist(self) -> str | None:
        """Return current media artist."""
        return self.coordinator.data.media_artist if self.coordinator.data else None

    @property
    def media_album_name(self) -> str | None:
        """Return current media album."""
        return self.coordinator.data.media_album if self.coordinator.data else None

    @property
    def media_image_url(self) -> str | None:
        """Return current media image URL."""
        return self.coordinator.data.media_image_url if self.coordinator.data else None

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return extra attributes."""
        data = self.coordinator.data
        return {
            "current_app": data.current_app if data else None,
            "raw_hdmi_input": data.raw_hdmi_input if data else None,
            "physical_sources": data.physical_sources if data else None,
            "apps": data.apps if data else None,
            "media_playback_state": data.media_playback_state if data else None,
            "media_playback_state_raw": (
                data.media_playback_state_raw if data else None
            ),
        }

    async def async_turn_on(self) -> None:
        """Turn on the TV."""
        await self.coordinator.runtime.async_turn_on()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self) -> None:
        """Turn off the TV."""
        await self.coordinator.runtime.async_turn_off()
        await self.coordinator.async_request_refresh()

    async def async_select_source(self, source: str) -> None:
        """Select a source."""
        await self.coordinator.runtime.async_select_source(source)
        await self.coordinator.async_request_refresh()

    async def async_set_volume_level(self, volume: float) -> None:
        """Set volume level."""
        await self.coordinator.hass.async_add_executor_job(
            self.coordinator.runtime._adb.set_volume_level,  # noqa: SLF001
            volume,
        )
        await self.coordinator.async_request_refresh()
