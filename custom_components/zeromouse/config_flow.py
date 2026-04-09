"""Config flow for ZeroMOUSE integration."""

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ZeromouseApiError, ZeromouseAuthError, async_validate_credentials
from .const import CONF_DEVICE_ID, CONF_DEVICE_NAME, CONF_REFRESH_TOKEN, DOMAIN

_LOGGER = logging.getLogger(__name__)


class ZeromouseConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ZeroMOUSE."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial setup step."""
        errors = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            try:
                await async_validate_credentials(
                    session,
                    user_input[CONF_DEVICE_ID],
                    user_input[CONF_REFRESH_TOKEN],
                )
            except ZeromouseAuthError:
                errors["base"] = "invalid_auth"
            except ZeromouseApiError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during config validation")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(user_input[CONF_DEVICE_ID])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=user_input.get(CONF_DEVICE_NAME, "ZeroMOUSE"),
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICE_ID): str,
                    vol.Required(CONF_REFRESH_TOKEN): str,
                    vol.Optional(CONF_DEVICE_NAME, default="ZeroMOUSE"): str,
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data):
        """Handle re-authentication when the refresh token expires."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        """Handle the re-auth confirmation step."""
        errors = {}

        reauth_entry = self._get_reauth_entry()

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            try:
                await async_validate_credentials(
                    session,
                    reauth_entry.data[CONF_DEVICE_ID],
                    user_input[CONF_REFRESH_TOKEN],
                )
            except ZeromouseAuthError:
                errors["base"] = "invalid_auth"
            except ZeromouseApiError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during reauth validation")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data={
                        **reauth_entry.data,
                        CONF_REFRESH_TOKEN: user_input[CONF_REFRESH_TOKEN],
                    },
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_REFRESH_TOKEN): str,
                }
            ),
            errors=errors,
        )
