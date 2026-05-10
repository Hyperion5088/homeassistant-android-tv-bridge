"""Select platform for Android TV Bridge."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
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
    """Set up select entities."""
    coordinator: AndroidTvBridgeCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([AndroidTvBridgeSourceSelect(coordinator)])


class AndroidTvBridgeSourceSelect(AndroidTvBridgeEntity, SelectEntity):
    """Source selector."""

    _attr_name = "Source"

    def __init__(self, coordinator: AndroidTvBridgeCoordinator) -> None:
        """Initialize the source selector."""
        super().__init__(coordinator, "source")

    @property
    def options(self) -> list[str]:
        """Return source options."""
        return self.coordinator.runtime.source_names()

    @property
    def current_option(self) -> str | None:
        """Return current source."""
        return self.coordinator.data.current_source if self.coordinator.data else None

    async def async_select_option(self, option: str) -> None:
        """Select a source."""
        await self.coordinator.runtime.async_select_source(option)
        await self.coordinator.async_request_refresh()
