from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .discovery import (
    EntityDiscoveryState,
    discover_inverter_sensor_entities,
    discover_power_plant_sensor_entities,
)
from .entity import (
    get_inverter_wn,
    get_power_plant,
    get_power_plant_value,
    inverters_are_online,
    is_energy_sensor_key,
    is_inverter_online,
    is_period_energy_key,
    normalize_energy_value,
    power_plant_device_info,
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    """Set up Invertechs sensors."""
    entry_data = hass.data[DOMAIN][entry.entry_id]
    coordinator = entry_data["coordinator"]
    fast_coordinator = entry_data["fast_coordinator"]
    discovery_state = EntityDiscoveryState()

    @callback
    def _add_fast_entities() -> None:
        entities = discover_power_plant_sensor_entities(
            fast_coordinator, entry, discovery_state
        )
        if entities:
            async_add_entities(entities)

    @callback
    def _add_device_entities() -> None:
        entities = discover_inverter_sensor_entities(
            coordinator, entry, discovery_state, fast_coordinator
        )
        if entities:
            async_add_entities(entities)

    _add_fast_entities()
    _add_device_entities()
    entry.async_on_unload(fast_coordinator.async_add_listener(_add_fast_entities))
    entry.async_on_unload(coordinator.async_add_listener(_add_device_entities))


class InvertechsSensorEntity(RestoreEntity, CoordinatorEntity, SensorEntity):
    """Base sensor with offline availability and energy normalization."""

    _attr_has_entity_name = True
    entity_description: SensorEntityDescription
    _last_energy_value: float | None = None
    _attr_last_reset: datetime | None = None

    async def async_added_to_hass(self) -> None:
        """Restore energy baselines and subscribe to connectivity updates."""
        await super().async_added_to_hass()
        if is_energy_sensor_key(self.entity_description.key):
            await self._async_restore_energy_baseline()

    async def _async_restore_energy_baseline(self) -> None:
        """Seed monotonic filters from the last persisted entity state."""
        if (last_state := await self.async_get_last_state()) is None:
            return
        if last_state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return
        try:
            self._last_energy_value = float(last_state.state)
        except (ValueError, TypeError):
            return

    def _normalize_energy(self, raw: Any) -> Any:
        """Apply monotonic and period-reset rules to an energy reading."""
        result = normalize_energy_value(
            self.entity_description.key,
            raw,
            self._last_energy_value,
            last_reset=(
                self._attr_last_reset
                if is_period_energy_key(self.entity_description.key)
                else None
            ),
        )
        self._last_energy_value = result.last_value
        if result.last_reset is not None:
            self._attr_last_reset = result.last_reset
        return result.value

    def _measurement_source_available(self) -> bool:
        """Return whether live measurements should be exposed."""
        raise NotImplementedError

    @property
    def available(self) -> bool:
        """Measurement sensors are unavailable when the inverter is offline."""
        if not super().available:
            return False
        if is_energy_sensor_key(self.entity_description.key):
            return True
        return self._measurement_source_available()


class InvertechsPowerPlantSensor(InvertechsSensorEntity):
    """Sensor for a power plant reading."""

    def __init__(
        self,
        coordinator,
        entry: ConfigEntry,
        power_plant: dict,
        description: SensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._power_plant_id = power_plant["id"]
        self._attr_unique_id = f"{entry.entry_id}_{power_plant['id']}_{description.key}"
        self._attr_device_info = power_plant_device_info(power_plant)

    def _measurement_source_available(self) -> bool:
        power_plant = get_power_plant(self.coordinator, self._power_plant_id)
        if not power_plant:
            return False
        return inverters_are_online(power_plant)

    @property
    def native_value(self):
        power_plant = get_power_plant(self.coordinator, self._power_plant_id)
        if not power_plant:
            return None
        raw = get_power_plant_value(power_plant, self.entity_description.key)
        if is_energy_sensor_key(self.entity_description.key):
            return self._normalize_energy(raw)
        return raw


class InvertechsInverterSensor(InvertechsSensorEntity):
    """Sensor for an inverter reading from detail polling."""

    def __init__(
        self,
        coordinator,
        entry: ConfigEntry,
        power_plant_id: str,
        wn_id: str,
        device_info,
        description: SensorEntityDescription,
        fast_coordinator,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._power_plant_id = power_plant_id
        self._wn_id = wn_id
        self._fast_coordinator = fast_coordinator
        self._attr_unique_id = f"{entry.entry_id}_{wn_id}_{description.key}"
        self._attr_device_info = device_info

    async def async_added_to_hass(self) -> None:
        """Listen to live connectivity updates for measurement sensors."""
        await super().async_added_to_hass()
        if is_energy_sensor_key(self.entity_description.key):
            return
        self.async_on_remove(
            self._fast_coordinator.async_add_listener(self.async_write_ha_state)
        )

    def _measurement_source_available(self) -> bool:
        power_plant = get_power_plant(self._fast_coordinator, self._power_plant_id)
        if not power_plant:
            return False
        return is_inverter_online(power_plant, self._wn_id)

    @property
    def native_value(self):
        wn = get_inverter_wn(self.coordinator, self._power_plant_id, self._wn_id)
        if not wn:
            return None
        raw = wn.get("details", {}).get(self.entity_description.key)
        if is_energy_sensor_key(self.entity_description.key):
            return self._normalize_energy(raw)
        return raw
