"""Shared helpers and entity descriptions for the Invertechs integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntityDescription
from homeassistant.components.sensor import SensorDeviceClass, SensorEntityDescription, SensorStateClass
from homeassistant.const import (
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .client import InvertechsClient
from .const import DOMAIN

MANUFACTURER = "Invertechs (Xiamen) Technology Co., Ltd."
DEVICE_TYPE_INVERTER = 0
POWER_PLANT_MODEL = "Solar Power Plant"


@dataclass(frozen=True)
class InverterInputSensorKeys:
    """API field names for one inverter DC input."""

    voltage: str
    current: str
    power: str
    voltage_translation_key: str
    current_translation_key: str
    power_translation_key: str


INVERTER_INPUT_SENSOR_KEYS: tuple[InverterInputSensorKeys, ...] = (
    InverterInputSensorKeys(
        "inputVoltage",
        "inputFirElectricity",
        "inputFirPower",
        "input_1_voltage",
        "input_1_current",
        "input_1_power",
    ),
    InverterInputSensorKeys(
        "inputSecVoltage",
        "inputSecElectricity",
        "inputSecPower",
        "input_2_voltage",
        "input_2_current",
        "input_2_power",
    ),
    InverterInputSensorKeys(
        "inputThirdVoltage",
        "inputThirdElectricity",
        "inputThirdPower",
        "input_3_voltage",
        "input_3_current",
        "input_3_power",
    ),
    InverterInputSensorKeys(
        "inputFourVoltage",
        "inputFourElectricity",
        "inputFourPower",
        "input_4_voltage",
        "input_4_current",
        "input_4_power",
    ),
    InverterInputSensorKeys(
        "fiveVolta",
        "fiveElect",
        "fivePower",
        "input_5_voltage",
        "input_5_current",
        "input_5_power",
    ),
    InverterInputSensorKeys(
        "sixVolta",
        "sixElect",
        "sixPower",
        "input_6_voltage",
        "input_6_current",
        "input_6_power",
    ),
)


def _energy_description(key: str, translation_key: str) -> SensorEntityDescription:
    return SensorEntityDescription(
        key=key,
        translation_key=translation_key,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    )


POWER_PLANT_SENSOR_DESCRIPTIONS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="power",
        translation_key="current_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    _energy_description("dayPowerGeneration", "daily_energy"),
    _energy_description("monthPowerGeneration", "monthly_energy"),
    _energy_description("yearPowerGeneration", "yearly_energy"),
    _energy_description("totalPowerGeneration", "total_energy"),
)

INVERTER_SENSOR_DESCRIPTIONS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="power",
        translation_key="current_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    _energy_description("dayPowerGeneration", "daily_energy"),
    _energy_description("monthPowerGeneration", "monthly_energy"),
    _energy_description("yearPowerGeneration", "yearly_energy"),
    _energy_description("totalPowerGeneration", "total_energy"),
    SensorEntityDescription(
        key="temp",
        translation_key="temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="outputVoltage",
        translation_key="output_voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="outputElectricity",
        translation_key="output_current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="outputFrequency",
        translation_key="output_frequency",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="outputPower",
        translation_key="output_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
)

POWER_PLANT_BINARY_SENSOR_DESCRIPTIONS: tuple[BinarySensorEntityDescription, ...] = (
    BinarySensorEntityDescription(
        key="stationOnlineStatus",
        translation_key="connection",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
    ),
    BinarySensorEntityDescription(
        key="isHaveAlarm",
        translation_key="status",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
)

INVERTER_BINARY_SENSOR_DESCRIPTIONS: tuple[BinarySensorEntityDescription, ...] = (
    BinarySensorEntityDescription(
        key="onlineStatus",
        translation_key="connection",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
    ),
    BinarySensorEntityDescription(
        key="alarmStatus",
        translation_key="status",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
)


def power_plant_device_info(power_plant: dict[str, Any]) -> DeviceInfo:
    """Build device registry info for a power plant."""
    return DeviceInfo(
        identifiers={(DOMAIN, power_plant["id"])},
        name=power_plant["stationName"],
        manufacturer=MANUFACTURER,
        model=POWER_PLANT_MODEL,
        model_id=power_plant["id"],
    )


def inverter_device_info(
    wn_id: str,
    wn_details: dict[str, Any],
    model: str,
    power_plant_id: str,
) -> DeviceInfo:
    """Build device registry info for an inverter."""
    return DeviceInfo(
        identifiers={(DOMAIN, wn_id)},
        name=f"Inver Energy {model}",
        manufacturer=MANUFACTURER,
        model=model,
        model_id=wn_details.get("wnId"),
        sw_version=wn_details.get("softwareVersion"),
        hw_version=wn_details.get("hardwareVersion"),
        via_device=(DOMAIN, power_plant_id),
    )


INVERTER_ONLINE_STATUS = 1


def inverters_are_online(power_plant: dict[str, Any]) -> bool:
    """Return True when at least one inverter reports online in live IoT data."""
    wn_list = get_live_data(power_plant).get("wnVoList") or []
    if not wn_list:
        return False
    return any(wn.get("onlineStatus") == INVERTER_ONLINE_STATUS for wn in wn_list)


def account_inverters_are_online(power_plants: list[dict[str, Any]]) -> bool:
    """Return True when any power plant has an online inverter."""
    if not power_plants:
        return True
    return any(inverters_are_online(power_plant) for power_plant in power_plants)


def get_live_data(power_plant: dict[str, Any]) -> dict[str, Any]:
    """Return the live IoT payload for a power plant."""
    live = power_plant.get("live")
    return live if isinstance(live, dict) else {}


def get_live_inverter(power_plant: dict[str, Any], wn_id: str) -> dict[str, Any] | None:
    """Return one inverter entry from live IoT data."""
    for wn in get_live_data(power_plant).get("wnVoList", []):
        if wn.get("wnId") == wn_id:
            return wn
    return None


def get_power_plant_value(power_plant: dict[str, Any], key: str) -> Any:
    """Return a plant metric from refreshed station details."""
    details = power_plant.get("details", {})
    if key in details and details[key] is not None:
        return details[key]
    return power_plant.get(key)


def get_inverter_power_limit_percent(power_plant: dict[str, Any], wn_id: str) -> float | None:
    """Return inverter power limit percent from live IoT data."""
    return InvertechsClient.get_inverter_power_limit_percent(get_live_data(power_plant), wn_id)


def inverter_device_info_from_live(
    wn: dict[str, Any],
    power_plant_id: str,
) -> DeviceInfo:
    """Build device registry info for an inverter using live IoT data."""
    model = wn.get("modelVersion") or "Unknown"
    return DeviceInfo(
        identifiers={(DOMAIN, wn["wnId"])},
        name=f"Inver Energy {model}",
        manufacturer=MANUFACTURER,
        model=model,
        model_id=wn.get("wnId"),
        sw_version=wn.get("softwareVersion"),
        hw_version=wn.get("hardwareVersion"),
        via_device=(DOMAIN, power_plant_id),
    )


def get_power_plant(
    coordinator: DataUpdateCoordinator[list[dict[str, Any]]],
    power_plant_id: str,
) -> dict[str, Any] | None:
    """Return a power plant dict from coordinator data."""
    if not coordinator.data:
        return None
    for power_plant in coordinator.data:
        if power_plant["id"] == power_plant_id:
            return power_plant
    return None


def get_inverter_wn(
    coordinator: DataUpdateCoordinator[list[dict[str, Any]]],
    power_plant_id: str,
    wn_id: str,
) -> dict[str, Any] | None:
    """Return an inverter wnStationVo dict from coordinator data."""
    power_plant = get_power_plant(coordinator, power_plant_id)
    if not power_plant:
        return None
    for device in power_plant.get("devices", []):
        wn = device.get("wnStationVo")
        if wn and wn.get("wnId") == wn_id:
            return wn
    return None


def inverter_input_sensor_description(
    api_key: str,
    translation_key: str,
    device_class: SensorDeviceClass,
    unit: str,
) -> SensorEntityDescription:
    """Build a sensor description for an inverter DC input reading."""
    return SensorEntityDescription(
        key=api_key,
        translation_key=translation_key,
        native_unit_of_measurement=unit,
        device_class=device_class,
        state_class=SensorStateClass.MEASUREMENT,
    )
