"""Config flow for the King Smith WalkingPad."""

from __future__ import annotations

import re
from typing import Any

import voluptuous as vol

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_MAC, CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.device_registry import format_mac

from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .coordinator import WalkingPadConfigEntry

MAC_RE = re.compile(r"^([0-9A-F]{2}:){5}[0-9A-F]{2}$")
NAME_PREFIXES = ("KS-BL", "KS-ST-", "WalkingPad")


def _is_walking_pad(info: bluetooth.BluetoothServiceInfoBleak) -> bool:
    return bool(info.name) and info.name.startswith(NAME_PREFIXES)


class WalkingPadConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the WalkingPad."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the flow."""
        self._discovered: bluetooth.BluetoothServiceInfoBleak | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: WalkingPadConfigEntry) -> OptionsFlow:
        """Return the options flow."""
        return WalkingPadOptionsFlow()

    async def async_step_bluetooth(
        self, discovery_info: bluetooth.BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle a pad found by Bluetooth discovery."""
        await self.async_set_unique_id(format_mac(discovery_info.address))
        self._abort_if_unique_id_configured()
        self._discovered = discovery_info
        self.context["title_placeholders"] = {"name": discovery_info.name}
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm a discovered pad and pick a name."""
        assert self._discovered is not None
        if user_input is not None:
            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data={
                    CONF_NAME: user_input[CONF_NAME],
                    CONF_MAC: self._discovered.address.upper(),
                },
            )
        return self.async_show_form(
            step_id="bluetooth_confirm",
            data_schema=vol.Schema(
                {vol.Required(CONF_NAME, default=self._discovered.name): str}
            ),
            description_placeholders={
                "name": self._discovered.name,
                "mac": self._discovered.address,
            },
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Set up a pad manually: pick a found one or enter the address."""
        errors: dict[str, str] = {}
        if user_input is not None:
            mac = user_input[CONF_MAC].split(" ")[0].strip().upper()
            if not MAC_RE.match(mac):
                errors[CONF_MAC] = "invalid_mac"
            else:
                await self.async_set_unique_id(format_mac(mac))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data={CONF_NAME: user_input[CONF_NAME], CONF_MAC: mac},
                )

        configured = self._async_current_ids(include_ignore=False)
        found = [
            selector.SelectOptionDict(
                value=info.address.upper(), label=f"{info.name} ({info.address})"
            )
            for info in bluetooth.async_discovered_service_info(self.hass)
            if _is_walking_pad(info) and format_mac(info.address) not in configured
        ]
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default="WalkingPad"): str,
                    vol.Required(CONF_MAC): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=found, custom_value=True)
                    ),
                }
            ),
            errors=errors,
        )


class WalkingPadOptionsFlow(OptionsFlow):
    """Options for an existing pad."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SCAN_INTERVAL, default=current): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                    )
                }
            ),
        )
