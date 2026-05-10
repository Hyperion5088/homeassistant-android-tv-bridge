"""Base entities for Android TV Bridge."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AndroidTvBridgeCoordinator


class AndroidTvBridgeEntity(CoordinatorEntity[AndroidTvBridgeCoordinator]):
    """Base bridge entity."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: AndroidTvBridgeCoordinator, suffix: str) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{suffix}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        state = self.coordinator.data
        model = None
        manufacturer = None
        if state and state.device_info:
            model = state.device_info.get("model")
            manufacturer = state.device_info.get("manufacturer")
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.entry.entry_id)},
            name=self.coordinator.runtime.name,
            manufacturer=manufacturer,
            model=model,
        )
