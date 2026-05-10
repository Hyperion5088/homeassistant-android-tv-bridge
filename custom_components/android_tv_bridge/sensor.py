"""Sensor platform for Android TV Bridge."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import AndroidTvBridgeCoordinator
from .entity import AndroidTvBridgeEntity

NOT_PROVIDED = "Not Provided"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities."""
    coordinator: AndroidTvBridgeCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            AndroidTvBridgeCurrentAppSensor(coordinator),
            AndroidTvBridgeRawInputSensor(coordinator),
            AndroidTvBridgePhysicalSourcesSensor(coordinator),
            AndroidTvBridgeAppsSensor(coordinator),
            AndroidTvBridgeMediaTitleSensor(coordinator),
            AndroidTvBridgeMediaArtistSensor(coordinator),
            AndroidTvBridgeMediaAlbumSensor(coordinator),
            AndroidTvBridgeMediaImageSensor(coordinator),
            AndroidTvBridgeMediaPlaybackStateSensor(coordinator),
        ]
    )


class AndroidTvBridgeCurrentAppSensor(AndroidTvBridgeEntity, SensorEntity):
    """Current app sensor."""

    _attr_name = "Current App"
    _attr_icon = "mdi:application"

    def __init__(self, coordinator: AndroidTvBridgeCoordinator) -> None:
        """Initialize sensor."""
        super().__init__(coordinator, "current_app")

    @property
    def native_value(self) -> str | None:
        """Return native value."""
        return self.coordinator.data.current_app if self.coordinator.data else None


class AndroidTvBridgeRawInputSensor(AndroidTvBridgeEntity, SensorEntity):
    """Raw HDMI input sensor."""

    _attr_name = "Raw HDMI Input"
    _attr_icon = "mdi:video-input-hdmi"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: AndroidTvBridgeCoordinator) -> None:
        """Initialize sensor."""
        super().__init__(coordinator, "raw_hdmi_input")

    @property
    def native_value(self) -> str | None:
        """Return native value."""
        return self.coordinator.data.raw_hdmi_input if self.coordinator.data else None


class AndroidTvBridgePhysicalSourcesSensor(AndroidTvBridgeEntity, SensorEntity):
    """Discovered physical sources sensor."""

    _attr_name = "Physical Sources"
    _attr_icon = "mdi:video-input-component"

    def __init__(self, coordinator: AndroidTvBridgeCoordinator) -> None:
        """Initialize sensor."""
        super().__init__(coordinator, "physical_sources")

    @property
    def native_value(self) -> int:
        """Return number of discovered physical sources."""
        if not self.coordinator.data or not self.coordinator.data.physical_sources:
            return 0
        return len(self.coordinator.data.physical_sources)

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return discovered source details."""
        sources = []
        if self.coordinator.data and self.coordinator.data.physical_sources:
            sources = self.coordinator.data.physical_sources
        return {"sources": sources}


class AndroidTvBridgeAppsSensor(AndroidTvBridgeEntity, SensorEntity):
    """Discovered apps sensor."""

    _attr_name = "Apps"
    _attr_icon = "mdi:apps"

    def __init__(self, coordinator: AndroidTvBridgeCoordinator) -> None:
        """Initialize sensor."""
        super().__init__(coordinator, "apps")

    @property
    def native_value(self) -> int:
        """Return number of discovered apps."""
        if not self.coordinator.data or not self.coordinator.data.apps:
            return 0
        return len(self.coordinator.data.apps)

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return discovered app details."""
        apps = []
        if self.coordinator.data and self.coordinator.data.apps:
            apps = self.coordinator.data.apps
        return {"apps": apps}


class AndroidTvBridgeMediaTitleSensor(AndroidTvBridgeEntity, SensorEntity):
    """Media title sensor."""

    _attr_name = "Media Title"
    _attr_icon = "mdi:format-title"

    def __init__(self, coordinator: AndroidTvBridgeCoordinator) -> None:
        """Initialize sensor."""
        super().__init__(coordinator, "media_title")

    @property
    def native_value(self) -> str | None:
        """Return native value."""
        if not self.coordinator.data:
            return NOT_PROVIDED
        return self.coordinator.data.media_title or NOT_PROVIDED


class AndroidTvBridgeMediaArtistSensor(AndroidTvBridgeEntity, SensorEntity):
    """Media artist sensor."""

    _attr_name = "Media Artist"
    _attr_icon = "mdi:account-music"

    def __init__(self, coordinator: AndroidTvBridgeCoordinator) -> None:
        """Initialize sensor."""
        super().__init__(coordinator, "media_artist")

    @property
    def native_value(self) -> str | None:
        """Return native value."""
        if not self.coordinator.data:
            return NOT_PROVIDED
        return self.coordinator.data.media_artist or NOT_PROVIDED


class AndroidTvBridgeMediaAlbumSensor(AndroidTvBridgeEntity, SensorEntity):
    """Media album sensor."""

    _attr_name = "Media Album"
    _attr_icon = "mdi:album"

    def __init__(self, coordinator: AndroidTvBridgeCoordinator) -> None:
        """Initialize sensor."""
        super().__init__(coordinator, "media_album")

    @property
    def native_value(self) -> str | None:
        """Return native value."""
        if not self.coordinator.data:
            return NOT_PROVIDED
        return self.coordinator.data.media_album or NOT_PROVIDED


class AndroidTvBridgeMediaImageSensor(AndroidTvBridgeEntity, SensorEntity):
    """Media image sensor."""

    _attr_name = "Media Image"
    _attr_icon = "mdi:image"

    def __init__(self, coordinator: AndroidTvBridgeCoordinator) -> None:
        """Initialize sensor."""
        super().__init__(coordinator, "media_image")

    @property
    def native_value(self) -> str | None:
        """Return native value."""
        if not self.coordinator.data:
            return NOT_PROVIDED
        return self.coordinator.data.media_image_url or NOT_PROVIDED


class AndroidTvBridgeMediaPlaybackStateSensor(AndroidTvBridgeEntity, SensorEntity):
    """Media playback state sensor."""

    _attr_name = "Media Playback State"
    _attr_icon = "mdi:play-circle-outline"

    def __init__(self, coordinator: AndroidTvBridgeCoordinator) -> None:
        """Initialize sensor."""
        super().__init__(coordinator, "media_playback_state")

    @property
    def native_value(self) -> str | None:
        """Return native value."""
        if not self.coordinator.data:
            return NOT_PROVIDED
        return self.coordinator.data.media_playback_state or NOT_PROVIDED

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return raw playback state details."""
        data = self.coordinator.data
        return {"raw_state": data.media_playback_state_raw if data else None}
