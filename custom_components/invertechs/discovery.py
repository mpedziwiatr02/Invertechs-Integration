"""Entity discovery helpers for dynamic platform setup."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfElectricCurrent, UnitOfElectricPotential, UnitOfPower
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .entity import (
    DEVICE_TYPE_INVERTER,
    INVERTER_BINARY_SENSOR_DESCRIPTIONS,
    INVERTER_INPUT_SENSOR_KEYS,
    INVERTER_SENSOR_DESCRIPTIONS,
    POWER_PLANT_BINARY_SENSOR_DESCRIPTIONS,
    POWER_PLANT_SENSOR_DESCRIPTIONS,
    get_live_data,
    inverter_device_info,
    inverter_device_info_from_live,
    inverter_input_sensor_description,
)


@dataclass
class EntityDiscoveryState:
    """Track entities already registered with Home Assistant."""

    registered_unique_ids: set[str] = field(default_factory=set)


def _register(
    state: EntityDiscoveryState,
    entry: ConfigEntry,
    unique_suffix: str,
) -> bool:
    """Return True when the entity is new and should be created."""
    unique_id = f"{entry.entry_id}_{unique_suffix}"
    if unique_id in state.registered_unique_ids:
        return False
    state.registered_unique_ids.add(unique_id)
    return True


def discover_power_plant_sensor_entities(
    power_plant_coordinator: DataUpdateCoordinator[list[dict[str, Any]]],
    entry: ConfigEntry,
    state: EntityDiscoveryState,
) -> list[Any]:
    """Build power plant sensor entities that are not yet registered."""
    from .sensor import InvertechsPowerPlantSensor

    entities: list[Any] = []
    for power_plant in power_plant_coordinator.data or []:
        power_plant_id = power_plant["id"]
        for description in POWER_PLANT_SENSOR_DESCRIPTIONS:
            if not _register(state, entry, f"{power_plant_id}_{description.key}"):
                continue
            entities.append(
                InvertechsPowerPlantSensor(
                    power_plant_coordinator, entry, power_plant, description
                )
            )
    return entities


def discover_inverter_sensor_entities(
    coordinator: DataUpdateCoordinator[list[dict[str, Any]]],
    entry: ConfigEntry,
    state: EntityDiscoveryState,
) -> list[Any]:
    """Build inverter detail sensor entities (slow polling)."""
    from .sensor import InvertechsInverterSensor

    entities: list[Any] = []
    for power_plant in coordinator.data or []:
        power_plant_id = power_plant["id"]
        for device in power_plant.get("devices", []):
            if device.get("devicesType") != DEVICE_TYPE_INVERTER or not device.get("wnStationVo"):
                continue

            wn = device["wnStationVo"]
            wn_details = wn.get("details", {})
            wn_id = wn["wnId"]
            model = wn_details.get("model", "Unknown")
            device_info = inverter_device_info(wn_id, wn_details, model, power_plant_id)

            for description in INVERTER_SENSOR_DESCRIPTIONS:
                if not _register(state, entry, f"{wn_id}_{description.key}"):
                    continue
                entities.append(
                    InvertechsInverterSensor(
                        coordinator, entry, power_plant_id, wn_id, device_info, description
                    )
                )

            for index, input_keys in enumerate(INVERTER_INPUT_SENSOR_KEYS):
                if wn_details.get("wnType", 0) < index + 1:
                    continue
                for description in (
                    inverter_input_sensor_description(
                        input_keys.voltage,
                        input_keys.voltage_translation_key,
                        SensorDeviceClass.VOLTAGE,
                        UnitOfElectricPotential.VOLT,
                    ),
                    inverter_input_sensor_description(
                        input_keys.current,
                        input_keys.current_translation_key,
                        SensorDeviceClass.CURRENT,
                        UnitOfElectricCurrent.AMPERE,
                    ),
                    inverter_input_sensor_description(
                        input_keys.power,
                        input_keys.power_translation_key,
                        SensorDeviceClass.POWER,
                        UnitOfPower.WATT,
                    ),
                ):
                    if not _register(state, entry, f"{wn_id}_{description.key}"):
                        continue
                    entities.append(
                        InvertechsInverterSensor(
                            coordinator, entry, power_plant_id, wn_id, device_info, description
                        )
                    )
    return entities


def discover_power_plant_binary_sensor_entities(
    power_plant_coordinator: DataUpdateCoordinator[list[dict[str, Any]]],
    entry: ConfigEntry,
    state: EntityDiscoveryState,
) -> list[Any]:
    """Build power plant binary sensor entities that are not yet registered."""
    from .binary_sensor import (
        InvertechsPowerPlantBinarySensor,
        InvertechsPowerPlantStatusBinarySensor,
    )

    entities: list[Any] = []
    for power_plant in power_plant_coordinator.data or []:
        power_plant_id = power_plant["id"]
        for description in POWER_PLANT_BINARY_SENSOR_DESCRIPTIONS:
            if not _register(state, entry, f"{power_plant_id}_{description.key}"):
                continue
            if description.key == "isHaveAlarm":
                entities.append(
                    InvertechsPowerPlantStatusBinarySensor(
                        power_plant_coordinator, entry, power_plant, description
                    )
                )
            else:
                entities.append(
                    InvertechsPowerPlantBinarySensor(
                        power_plant_coordinator, entry, power_plant, description
                    )
                )
    return entities


def discover_inverter_live_binary_sensor_entities(
    fast_coordinator: DataUpdateCoordinator[list[dict[str, Any]]],
    entry: ConfigEntry,
    state: EntityDiscoveryState,
) -> list[Any]:
    """Build inverter connection binary sensors from live IoT data."""
    from .binary_sensor import InvertechsInverterLiveBinarySensor

    entities: list[Any] = []
    connection_description = INVERTER_BINARY_SENSOR_DESCRIPTIONS[0]
    for power_plant in fast_coordinator.data or []:
        power_plant_id = power_plant["id"]
        for wn in get_live_data(power_plant).get("wnVoList", []):
            wn_id = wn.get("wnId")
            if not wn_id:
                continue
            if not _register(state, entry, f"{wn_id}_{connection_description.key}"):
                continue
            entities.append(
                InvertechsInverterLiveBinarySensor(
                    fast_coordinator,
                    entry,
                    power_plant_id,
                    wn_id,
                    inverter_device_info_from_live(wn, power_plant_id),
                    connection_description,
                )
            )
    return entities


def discover_inverter_binary_sensor_entities(
    coordinator: DataUpdateCoordinator[list[dict[str, Any]]],
    entry: ConfigEntry,
    state: EntityDiscoveryState,
) -> list[Any]:
    """Build inverter alarm binary sensor entities from detail polling."""
    from .binary_sensor import InvertechsInverterStatusBinarySensor

    entities: list[Any] = []
    alarm_description = INVERTER_BINARY_SENSOR_DESCRIPTIONS[1]
    for power_plant in coordinator.data or []:
        power_plant_id = power_plant["id"]
        for device in power_plant.get("devices", []):
            if device.get("devicesType") != DEVICE_TYPE_INVERTER or not device.get("wnStationVo"):
                continue

            wn = device["wnStationVo"]
            wn_details = wn.get("details", {})
            wn_id = wn["wnId"]
            model = wn_details.get("model", "Unknown")
            device_info = inverter_device_info(wn_id, wn_details, model, power_plant_id)

            if not _register(state, entry, f"{wn_id}_{alarm_description.key}"):
                continue
            entities.append(
                InvertechsInverterStatusBinarySensor(
                    coordinator,
                    entry,
                    power_plant_id,
                    wn_id,
                    device_info,
                    alarm_description,
                )
            )
    return entities


def discover_inverter_power_limit_entities(
    fast_coordinator: DataUpdateCoordinator[list[dict[str, Any]]],
    entry: ConfigEntry,
    state: EntityDiscoveryState,
) -> list[Any]:
    """Build inverter power limit number entities."""
    from .number import InvertechsInverterPowerLimitNumber

    entities: list[Any] = []
    for power_plant in fast_coordinator.data or []:
        power_plant_id = power_plant["id"]
        for wn in get_live_data(power_plant).get("wnVoList", []):
            wn_id = wn.get("wnId")
            if not wn_id:
                continue
            if not _register(state, entry, f"{wn_id}_power_limit_percent"):
                continue
            entities.append(
                InvertechsInverterPowerLimitNumber(
                    fast_coordinator,
                    entry,
                    power_plant_id,
                    wn_id,
                    inverter_device_info_from_live(wn, power_plant_id),
                )
            )
    return entities
