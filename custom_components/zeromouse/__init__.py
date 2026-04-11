"""The ZeroMOUSE integration."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CognitoAuth, EventClient, ShadowClient
from .const import (
    CONF_DEVICE_ID,
    CONF_REFRESH_TOKEN,
    DATA_EVENT_COORDINATOR,
    DATA_SHADOW_COORDINATOR,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import ZeromouseEventCoordinator, ZeromouseShadowCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ZeroMOUSE from a config entry."""
    session = async_get_clientsession(hass)
    device_id = entry.data[CONF_DEVICE_ID]
    refresh_token = entry.data[CONF_REFRESH_TOKEN]

    # Shared auth instance for both API clients
    auth = CognitoAuth(session, refresh_token)

    # API clients
    shadow_client = ShadowClient(auth, session, device_id)
    event_client = EventClient(auth, session, device_id)

    # Coordinators
    shadow_coordinator = ZeromouseShadowCoordinator(hass, shadow_client)
    event_coordinator = ZeromouseEventCoordinator(hass, event_client)

    # Initial data fetch — raises ConfigEntryAuthFailed or ConfigEntryNotReady
    await shadow_coordinator.async_config_entry_first_refresh()
    await event_coordinator.async_config_entry_first_refresh()

    # Store for platform setup
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        DATA_SHADOW_COORDINATOR: shadow_coordinator,
        DATA_EVENT_COORDINATOR: event_coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a ZeroMOUSE config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
