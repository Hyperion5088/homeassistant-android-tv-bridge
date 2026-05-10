"""Remote platform for Android TV Bridge."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from homeassistant.components.remote import RemoteEntity
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
    """Set up remote entities."""
    coordinator: AndroidTvBridgeCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([AndroidTvBridgeRemote(coordinator)])


class AndroidTvBridgeRemote(AndroidTvBridgeEntity, RemoteEntity):
    """Remote entity."""

    _attr_name = "Remote"

    def __init__(self, coordinator: AndroidTvBridgeCoordinator) -> None:
        """Initialize remote."""
        super().__init__(coordinator, "remote")

    @property
    def is_on(self) -> bool | None:
        """Return power state."""
        return self.coordinator.data.power_on if self.coordinator.data else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on."""
        await self.coordinator.runtime.async_turn_on()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off."""
        await self.coordinator.runtime.async_turn_off()
        await self.coordinator.async_request_refresh()

    async def async_send_command(
        self,
        command: Iterable[str],
        **kwargs: Any,
    ) -> None:
        """Send remote commands."""
        for item in command:
            await self.coordinator.runtime.async_send_key(item)
        await self.coordinator.async_request_refresh()
