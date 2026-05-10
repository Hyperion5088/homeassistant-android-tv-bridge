"""Config flow for Android TV Bridge."""

from __future__ import annotations

import json
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.selector import (
    BooleanSelector,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_ADB_KEY_PATH,
    CONF_DEVICE_CLASS,
    CONF_ENABLE_REMOTE_PROTOCOL,
    CONF_HIDDEN_APPS,
    CONF_HIDDEN_SOURCES,
    CONF_HOST,
    CONF_NAME,
    CONF_POLL_INTERVAL,
    CONF_PROFILE,
    CONF_SOURCE_MAP,
    DEVICE_CLASS_ANDROID_TV,
    DEVICE_CLASS_FIRE_TV,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
    MIN_POLL_INTERVAL,
    PROFILE_FIRE_TV,
    PROFILE_GENERIC,
    PROFILE_TCL_GOOGLE_TV,
)
from .profiles import friendly_app_name, parse_sources, source_map_json
from .runtime import AndroidTvBridgeRuntime

PROFILE_SELECTOR = SelectSelector(
    SelectSelectorConfig(
        options=[
            {"value": PROFILE_TCL_GOOGLE_TV, "label": "TCL Google TV"},
            {"value": PROFILE_FIRE_TV, "label": "Fire TV"},
            {"value": PROFILE_GENERIC, "label": "Generic Android TV"},
        ]
    )
)

DEVICE_CLASS_SELECTOR = SelectSelector(
    SelectSelectorConfig(
        options=[
            {"value": "auto", "label": "Auto"},
            {"value": DEVICE_CLASS_ANDROID_TV, "label": "Android TV"},
            {"value": DEVICE_CLASS_FIRE_TV, "label": "Fire TV"},
        ]
    )
)

EMPTY_MULTI_SELECT = SelectSelector(
    SelectSelectorConfig(options=[], multiple=True, mode=SelectSelectorMode.DROPDOWN)
)


class AndroidTvBridgeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle an Android TV Bridge config flow."""

    VERSION = 1
    _user_input: dict[str, Any]
    _app_options: list[dict[str, str]]
    _source_options: list[dict[str, str]]

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle manual setup."""
        errors: dict[str, str] = {}
        defaults = {
            CONF_PROFILE: PROFILE_TCL_GOOGLE_TV,
            CONF_DEVICE_CLASS: "auto",
            CONF_ENABLE_REMOTE_PROTOCOL: True,
            CONF_POLL_INTERVAL: DEFAULT_POLL_INTERVAL,
        }

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_HOST])
            self._abort_if_unique_id_configured()
            profile = user_input[CONF_PROFILE]
            self._user_input = dict(user_input)
            self._user_input[CONF_SOURCE_MAP] = source_map_json(profile)
            self._app_options, self._source_options = await self._poll_filter_options(
                self._user_input
            )
            return await self.async_step_filters()

        profile = (
            user_input.get(CONF_PROFILE)
            if user_input is not None
            else defaults[CONF_PROFILE]
        )
        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default="Android TV"): str,
                vol.Required(CONF_HOST, default=""): str,
                vol.Required(
                    CONF_PROFILE,
                    default=profile,
                ): PROFILE_SELECTOR,
                vol.Required(
                    CONF_DEVICE_CLASS,
                    default=defaults[CONF_DEVICE_CLASS],
                ): DEVICE_CLASS_SELECTOR,
                vol.Optional(
                    CONF_ADB_KEY_PATH,
                    default=self.hass.config.path(".storage/androidtv_adbkey"),
                ): str,
                vol.Required(
                    CONF_ENABLE_REMOTE_PROTOCOL,
                    default=defaults[CONF_ENABLE_REMOTE_PROTOCOL],
                ): BooleanSelector(),
                vol.Required(
                    CONF_POLL_INTERVAL,
                    default=defaults[CONF_POLL_INTERVAL],
                ): vol.All(vol.Coerce(int), vol.Range(min=MIN_POLL_INTERVAL)),
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_filters(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle source filter setup after a temporary source poll."""
        if user_input is not None:
            data = dict(self._user_input)
            data[CONF_HIDDEN_APPS] = user_input.get(CONF_HIDDEN_APPS, [])
            data[CONF_HIDDEN_SOURCES] = user_input.get(CONF_HIDDEN_SOURCES, [])
            return self.async_create_entry(title=data[CONF_NAME], data=data)

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_HIDDEN_APPS,
                    default=[],
                ): self._multi_select(self._app_options),
                vol.Optional(
                    CONF_HIDDEN_SOURCES,
                    default=[],
                ): self._multi_select(self._source_options),
            }
        )
        return self.async_show_form(step_id="filters", data_schema=schema)

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> AndroidTvBridgeOptionsFlow:
        """Create the options flow."""
        return AndroidTvBridgeOptionsFlow(config_entry)

    async def _poll_filter_options(
        self,
        user_input: dict[str, Any],
    ) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
        """Temporarily connect and poll enough state to build filter choices."""
        sources = parse_sources(user_input[CONF_SOURCE_MAP])
        runtime = AndroidTvBridgeRuntime(self.hass, "config_flow", user_input, sources)
        try:
            await runtime.async_setup()
            await runtime.async_update()
            await runtime.async_update()
            return runtime.app_filter_options(), runtime.source_filter_options()
        except Exception:  # noqa: BLE001
            return self._filter_options_from_source_map(user_input[CONF_SOURCE_MAP])
        finally:
            await runtime.async_close()

    @staticmethod
    def _filter_options_from_source_map(
        source_map: str,
    ) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
        """Build fallback filter choices from configured sources."""
        app_options: dict[str, str] = {}
        source_options: dict[str, str] = {}
        try:
            sources = parse_sources(source_map)
        except (ValueError, TypeError, json.JSONDecodeError):
            sources = []
        for source in sources:
            if source.kind.value == "app":
                app_options[source.value] = source.name
            else:
                source_options[source.value] = source.name
        return (
            AndroidTvBridgeOptionsFlow._sorted_options(app_options),
            AndroidTvBridgeOptionsFlow._sorted_options(source_options),
        )

    @staticmethod
    def _multi_select(options: list[dict[str, str]]) -> SelectSelector:
        """Return a multi-select selector for filter options."""
        if not options:
            return EMPTY_MULTI_SELECT
        return SelectSelector(
            SelectSelectorConfig(
                options=options,
                multiple=True,
                mode=SelectSelectorMode.DROPDOWN,
            )
        )


class AndroidTvBridgeOptionsFlow(config_entries.OptionsFlow):
    """Handle Android TV Bridge options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize the options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Manage integration options."""
        if user_input is not None:
            errors: dict[str, str] = {}
            options = dict(user_input)
            options[CONF_SOURCE_MAP] = self._config_entry.options.get(
                CONF_SOURCE_MAP,
                self._config_entry.data.get(
                    CONF_SOURCE_MAP,
                    source_map_json(
                        self._config_entry.data.get(CONF_PROFILE, PROFILE_GENERIC)
                    ),
                ),
            )
            return self.async_create_entry(title="", data=options)
        else:
            errors = {}

        current_interval = self._config_entry.options.get(
            CONF_POLL_INTERVAL,
            self._config_entry.data.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL),
        )
        source_map = self._config_entry.options.get(
            CONF_SOURCE_MAP,
            self._config_entry.data.get(
                CONF_SOURCE_MAP,
                source_map_json(self._config_entry.data.get(CONF_PROFILE, PROFILE_GENERIC)),
            ),
        )
        current_host = self._config_entry.options.get(
            CONF_HOST,
            self._config_entry.data.get(CONF_HOST, ""),
        )
        current_hidden_apps = self._config_entry.options.get(CONF_HIDDEN_APPS, [])
        current_hidden_sources = self._config_entry.options.get(CONF_HIDDEN_SOURCES, [])
        app_options, source_options = self._filter_options(source_map)
        app_options = self._include_selected(app_options, current_hidden_apps)
        source_options = self._include_selected(source_options, current_hidden_sources)
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_HOST,
                    default=(
                        user_input.get(CONF_HOST)
                        if user_input is not None
                        else current_host
                    ),
                ): str,
                vol.Required(
                    CONF_POLL_INTERVAL,
                    default=(
                        user_input.get(CONF_POLL_INTERVAL)
                        if user_input is not None
                        else current_interval
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=MIN_POLL_INTERVAL)),
                vol.Optional(
                    CONF_HIDDEN_APPS,
                    default=(
                        user_input.get(CONF_HIDDEN_APPS)
                        if user_input is not None
                        else current_hidden_apps
                    ),
                ): self._multi_select(app_options),
                vol.Optional(
                    CONF_HIDDEN_SOURCES,
                    default=(
                        user_input.get(CONF_HIDDEN_SOURCES)
                        if user_input is not None
                        else current_hidden_sources
                    ),
                ): self._multi_select(source_options),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)

    def _filter_options(
        self,
        source_map: str,
    ) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
        """Return discovered app and source filter options."""
        app_options: dict[str, str] = {}
        source_options: dict[str, str] = {}
        try:
            sources = parse_sources(source_map)
        except (ValueError, TypeError, json.JSONDecodeError):
            sources = []
        for source in sources:
            if source.kind.value == "app":
                app_options[source.value] = source.name
            else:
                source_options[source.value] = source.name

        coordinator = self.hass.data.get(DOMAIN, {}).get(self._config_entry.entry_id)
        if coordinator is not None:
            runtime = coordinator.runtime
            app_options.update(
                {option["value"]: option["label"] for option in runtime.app_filter_options()}
            )
            source_options.update(
                {
                    option["value"]: option["label"]
                    for option in runtime.source_filter_options()
                }
            )
        return (
            self._sorted_options(app_options),
            self._sorted_options(source_options),
        )

    @staticmethod
    def _multi_select(options: list[dict[str, str]]) -> SelectSelector:
        """Return a multi-select selector for filter options."""
        if not options:
            return EMPTY_MULTI_SELECT
        return SelectSelector(
            SelectSelectorConfig(
                options=options,
                multiple=True,
                mode=SelectSelectorMode.DROPDOWN,
            )
        )

    @staticmethod
    def _include_selected(
        options: list[dict[str, str]],
        selected: list[str],
    ) -> list[dict[str, str]]:
        """Keep selected hidden values available when discovery is not populated."""
        known = {option["value"] for option in options}
        merged = list(options)
        for value in selected:
            if value not in known:
                merged.append({"value": value, "label": friendly_app_name(value)})
        return sorted(merged, key=lambda option: option["label"].lower())

    @staticmethod
    def _sorted_options(options: dict[str, str]) -> list[dict[str, str]]:
        """Return sorted selector option dictionaries."""
        return [
            {"value": value, "label": label}
            for value, label in sorted(options.items(), key=lambda item: item[1].lower())
        ]
