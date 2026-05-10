"""Android TV Bridge integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_SOURCE_MAP, DOMAIN, PLATFORMS
from .coordinator import AndroidTvBridgeCoordinator
from .profiles import parse_sources
from .runtime import AndroidTvBridgeRuntime

AndroidTvBridgeConfigEntry = ConfigEntry[AndroidTvBridgeCoordinator]
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AndroidTvBridgeConfigEntry,
) -> bool:
    """Set up Android TV Bridge from a config entry."""
    runtime_data = dict(entry.data)
    runtime_data.update(entry.options)
    sources = parse_sources(runtime_data[CONF_SOURCE_MAP])
    runtime = AndroidTvBridgeRuntime(hass, entry.entry_id, runtime_data, sources)
    await runtime.async_setup()

    coordinator = AndroidTvBridgeCoordinator(hass, entry, runtime)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: AndroidTvBridgeConfigEntry,
) -> bool:
    """Unload a config entry."""
    try:
        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    except ValueError as err:
        if "Config entry was never loaded" not in str(err):
            raise
        _LOGGER.debug(
            "Ignoring partial unload for %s because platforms were already unloaded",
            entry.title,
        )
        unload_ok = True

    coordinator = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if coordinator is not None:
        await coordinator.runtime.async_close()
    return unload_ok


async def async_reload_entry(
    hass: HomeAssistant,
    entry: AndroidTvBridgeConfigEntry,
) -> None:
    """Reload the config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
