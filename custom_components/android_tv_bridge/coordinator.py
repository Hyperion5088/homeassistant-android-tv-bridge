"""Coordinator for Android TV Bridge."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL, DOMAIN
from .models import BridgeState
from .runtime import AndroidTvBridgeRuntime

_LOGGER = logging.getLogger(__name__)


class AndroidTvBridgeCoordinator(DataUpdateCoordinator[BridgeState]):
    """Update coordinator for a bridge device."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        runtime: AndroidTvBridgeRuntime,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            logger=_LOGGER,
            name=f"{DOMAIN}-{entry.entry_id}",
            update_interval=timedelta(
                seconds=entry.options.get(
                    CONF_POLL_INTERVAL,
                    entry.data.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL),
                )
            ),
        )
        self.entry = entry
        self.runtime = runtime

    async def _async_update_data(self) -> BridgeState:
        """Fetch latest state."""
        return await self.runtime.async_update()
