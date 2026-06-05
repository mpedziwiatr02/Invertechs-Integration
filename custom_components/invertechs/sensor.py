from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
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
        entities = discover_inverter_sensor_entities(coordinator, entry, discovery_state)
        if entities:
            async_add_entities(entities)

    _add_fast_entities()
    _add_device_entities()
    entry.async_on_unload(fast_coordinator.async_add_listener(_add_fast_entities))
    entry.async_on_unload(coordinator.async_add_listener(_add_device_entities))


class InvertechsPowerPlantSensor(CoordinatorEntity, SensorEntity):
    """Sensor for a power plant reading."""

    _attr_has_entity_name = True
    entity_description: SensorEntityDescription

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

    @property
    def native_value(self):
        power_plant = get_power_plant(self.coordinator, self._power_plant_id)
        if not power_plant:
            return None
        return get_power_plant_value(power_plant, self.entity_description.key)


class InvertechsInverterSensor(CoordinatorEntity, SensorEntity):
    """Sensor for an inverter reading from detail polling."""

    _attr_has_entity_name = True
    entity_description: SensorEntityDescription

    def __init__(
        self,
        coordinator,
        entry: ConfigEntry,
        power_plant_id: str,
        wn_id: str,
        device_info,
        description: SensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._power_plant_id = power_plant_id
        self._wn_id = wn_id
        self._attr_unique_id = f"{entry.entry_id}_{wn_id}_{description.key}"
        self._attr_device_info = device_info

    @property
    def native_value(self):
        wn = get_inverter_wn(self.coordinator, self._power_plant_id, self._wn_id)
        if not wn:
            return None
        return wn.get("details", {}).get(self.entity_description.key)
