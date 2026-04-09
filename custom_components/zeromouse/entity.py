"""Base entity for ZeroMOUSE integration."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator

from .const import DOMAIN


class ZeromouseEntity(CoordinatorEntity):
    """Base class for all ZeroMOUSE entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        device_id: str,
        device_name: str,
    ) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._device_name = device_name

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info shared by all entities."""
        sw_version = None
        if isinstance(self.coordinator.data, dict) and "system" in self.coordinator.data:
            sys_data = self.coordinator.data["system"]
            sw_version = (
                f"{sys_data.get('verMajor', 0)}"
                f".{sys_data.get('verMinor', 0)}"
                f".{sys_data.get('verRevision', 0)}"
            )

        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=self._device_name,
            manufacturer="ZeroMOUSE",
            model="ZeroMOUSE 2.0",
            sw_version=sw_version,
        )
