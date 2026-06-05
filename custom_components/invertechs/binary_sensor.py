from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .discovery import (
    EntityDiscoveryState,
    discover_inverter_binary_sensor_entities,
    discover_inverter_live_binary_sensor_entities,
    discover_power_plant_binary_sensor_entities,
)
from .entity import (
    get_live_inverter,
    get_inverter_wn,
    get_power_plant,
    get_power_plant_value,
    power_plant_device_info,
)

BINARY_SENSOR_ON_VALUES: dict[str, bool | int] = {
    "stationOnlineStatus": True,
    "isHaveAlarm": 1,
    "onlineStatus": 1,
    "alarmStatus": True,
}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    """Set up Invertechs binary sensors."""
    entry_data = hass.data[DOMAIN][entry.entry_id]
    coordinator = entry_data["coordinator"]
    fast_coordinator = entry_data["fast_coordinator"]
    discovery_state = EntityDiscoveryState()

    @callback
    def _add_fast_entities() -> None:
        entities = [
            *discover_power_plant_binary_sensor_entities(fast_coordinator, entry, discovery_state),
            *discover_inverter_live_binary_sensor_entities(fast_coordinator, entry, discovery_state),
        ]
        if entities:
            async_add_entities(entities)

    @callback
    def _add_device_entities() -> None:
        entities = discover_inverter_binary_sensor_entities(coordinator, entry, discovery_state)
        if entities:
            async_add_entities(entities)

    _add_fast_entities()
    _add_device_entities()
    entry.async_on_unload(fast_coordinator.async_add_listener(_add_fast_entities))
    entry.async_on_unload(coordinator.async_add_listener(_add_device_entities))


class InvertechsPowerPlantBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for a power plant."""

    _attr_has_entity_name = True
    entity_description: BinarySensorEntityDescription

    def __init__(
        self,
        coordinator,
        entry: ConfigEntry,
        power_plant: dict,
        description: BinarySensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._power_plant_id = power_plant["id"]
        self._on_value = BINARY_SENSOR_ON_VALUES[description.key]
        self._attr_unique_id = f"{entry.entry_id}_{power_plant['id']}_{description.key}"
        self._attr_device_info = power_plant_device_info(power_plant)

    @property
    def is_on(self) -> bool:
        power_plant = get_power_plant(self.coordinator, self._power_plant_id)
        if not power_plant:
            return False
        value = get_power_plant_value(power_plant, self.entity_description.key)
        return value == self._on_value if value is not None else False


class InvertechsPowerPlantStatusBinarySensor(InvertechsPowerPlantBinarySensor):
    """Power plant status binary sensor with diagnostic attributes."""

    @property
    def extra_state_attributes(self) -> dict | None:
        power_plant = get_power_plant(self.coordinator, self._power_plant_id)
        if not power_plant:
            return None
        return {
            "creation_time": power_plant.get("createTime"),
            "plant_address": power_plant.get("stationAddress"),
            "capacity": power_plant.get("capacity"),
            "inverters_count": power_plant.get("wnNum"),
            "meter_exists": bool(power_plant.get("existsMeter")),
            "battery_exists": bool(power_plant.get("existsBattery")),
        }


class InvertechsInverterLiveBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Inverter connection binary sensor from live IoT data."""

    _attr_has_entity_name = True
    entity_description: BinarySensorEntityDescription

    def __init__(
        self,
        coordinator,
        entry: ConfigEntry,
        power_plant_id: str,
        wn_id: str,
        device_info,
        description: BinarySensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._power_plant_id = power_plant_id
        self._wn_id = wn_id
        self._on_value = BINARY_SENSOR_ON_VALUES[description.key]
        self._attr_unique_id = f"{entry.entry_id}_{wn_id}_{description.key}"
        self._attr_device_info = device_info

    @property
    def is_on(self) -> bool:
        power_plant = get_power_plant(self.coordinator, self._power_plant_id)
        if not power_plant:
            return False
        wn = get_live_inverter(power_plant, self._wn_id)
        if not wn:
            return False
        value = wn.get(self.entity_description.key)
        return value == self._on_value if value is not None else False


class InvertechsInverterBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for an inverter from detail polling."""

    _attr_has_entity_name = True
    entity_description: BinarySensorEntityDescription

    def __init__(
        self,
        coordinator,
        entry: ConfigEntry,
        power_plant_id: str,
        wn_id: str,
        device_info,
        description: BinarySensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._power_plant_id = power_plant_id
        self._wn_id = wn_id
        self._on_value = BINARY_SENSOR_ON_VALUES[description.key]
        self._attr_unique_id = f"{entry.entry_id}_{wn_id}_{description.key}"
        self._attr_device_info = device_info

    @property
    def is_on(self) -> bool:
        wn = get_inverter_wn(self.coordinator, self._power_plant_id, self._wn_id)
        if not wn:
            return False
        details = wn.get("details", {})
        value = details.get(self.entity_description.key, wn.get(self.entity_description.key))
        return value == self._on_value if value is not None else False


class InvertechsInverterStatusBinarySensor(InvertechsInverterBinarySensor):
    """Inverter status binary sensor with diagnostic attributes."""

    @property
    def extra_state_attributes(self) -> dict | None:
        wn = get_inverter_wn(self.coordinator, self._power_plant_id, self._wn_id)
        if not wn:
            return None
        details = wn.get("details", {})
        pd_month = wn.get("pdMonth", "")
        return {
            "plant_name": details.get("stationName"),
            "production_month": (
                f"{pd_month[:-2]}-{pd_month[-2:]}" if len(pd_month) >= 2 else ""
            ),
            "valid_thru": wn.get("validDate"),
            "rated_power": details.get("ratedPower"),
            "inverter_type": details.get("wnType"),
        }
