"""Number platform for Invertechs inverter controls."""

from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .client import InvertechsApiError, InvertechsAuthError, InvertechsError
from .const import (
    DOMAIN,
    POWER_LIMIT_MAX_PERCENT,
    POWER_LIMIT_MIN_PERCENT,
)
from .discovery import EntityDiscoveryState, discover_inverter_power_limit_entities
from .entity import get_inverter_power_limit_percent, get_power_plant

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    """Set up Invertechs number entities."""
    entry_data = hass.data[DOMAIN][entry.entry_id]
    fast_coordinator = entry_data["fast_coordinator"]
    discovery_state = EntityDiscoveryState()

    @callback
    def _add_entities() -> None:
        entities = discover_inverter_power_limit_entities(
            fast_coordinator, entry, discovery_state
        )
        if entities:
            async_add_entities(entities)

    _add_entities()
    entry.async_on_unload(fast_coordinator.async_add_listener(_add_entities))


class InvertechsInverterPowerLimitNumber(CoordinatorEntity, NumberEntity):
    """Set the inverter active power limit (percent of rated power)."""

    _attr_has_entity_name = True
    _attr_translation_key = "power_limit_percent"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_native_min_value = POWER_LIMIT_MIN_PERCENT
    _attr_native_max_value = POWER_LIMIT_MAX_PERCENT
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER
    _attr_icon = "mdi:speedometer"

    def __init__(
        self,
        coordinator,
        entry: ConfigEntry,
        power_plant_id: str,
        wn_id: str,
        device_info,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._power_plant_id = power_plant_id
        self._wn_id = wn_id
        self._attr_unique_id = f"{entry.entry_id}_{wn_id}_power_limit_percent"
        self._attr_device_info = device_info

    def _reported_percent(self) -> int | None:
        """Return the power limit currently reported by the API (whole percent)."""
        power_plant = get_power_plant(self.coordinator, self._power_plant_id)
        if not power_plant:
            return None
        value = get_inverter_power_limit_percent(power_plant, self._wn_id)
        return round(value) if value is not None else None

    async def async_added_to_hass(self) -> None:
        """Set the initial slider position from coordinator data."""
        await super().async_added_to_hass()
        self._attr_native_value = self._reported_percent()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Keep the slider aligned with the last API reading."""
        self._attr_native_value = self._reported_percent()
        self.async_write_ha_state()

    @callback
    def _restore_reported_value(self, value: int | None) -> None:
        """Revert the slider after a failed write."""
        self._attr_native_value = value
        self.async_write_ha_state()

    async def async_set_native_value(self, value: float) -> None:
        """Set inverter power limit via the mobile app API."""
        previous = self._reported_percent()
        clamped = round(
            max(
                POWER_LIMIT_MIN_PERCENT,
                min(POWER_LIMIT_MAX_PERCENT, float(value)),
            )
        )
        client = self.hass.data[DOMAIN][self._entry.entry_id]["client"]
        try:
            await client.set_inverter_power_percent(self._wn_id, clamped)
        except InvertechsAuthError as err:
            self._restore_reported_value(previous)
            raise HomeAssistantError(f"Authentication failed: {err}") from err
        except (InvertechsApiError, InvertechsError) as err:
            self._restore_reported_value(previous)
            raise HomeAssistantError(f"Could not set power limit: {err}") from err

        await self.coordinator.async_request_refresh()
