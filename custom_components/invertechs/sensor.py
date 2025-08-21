from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfPower,
    UnitOfEnergy,
    UnitOfElectricPotential,
    UnitOfElectricCurrent,
    UnitOfFrequency,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]

    entities = []

    for station in coordinator.data:
        station_id = station["id"]
        station_name = station["stationName"]
        station_details = station.get("details", {})

        # Station sensors
        entities.append(StationPowerSensor(coordinator, entry, station))
        entities.append(StationDailyEnergySensor(coordinator, entry, station))
        entities.append(StationMonthlyEnergySensor(coordinator, entry, station))
        entities.append(StationYearlyEnergySensor(coordinator, entry, station))
        entities.append(StationTotalEnergySensor(coordinator, entry, station))

        # Inverter sensors
        for device in station.get("devices", []):
            if device.get("devicesType") == 0 and device.get("wnStationVo"):
                wn = device["wnStationVo"]
                wn_details = wn.get("details", {})
                wn_id = wn["wnId"]
                model = wn_details.get("model", "Unknown")

                inverter_device_info = DeviceInfo(
                    identifiers={(DOMAIN, wn_id)},
                    name=f"Inver Energy {model}",
                    manufacturer="Invertechs (Xiamen) Technology Co., Ltd.",
                    model=model,
                    model_id=wn_details.get("wnId"),
                    sw_version=wn_details.get("softwareVersion"),
                    hw_version=wn_details.get("hardwareVersion"),
                    via_device=(DOMAIN, station_id),
                )

                entities.append(InverterPowerSensor(coordinator, entry, station_id, wn_id, inverter_device_info))
                entities.append(InverterDailyEnergySensor(coordinator, entry, station_id, wn_id, inverter_device_info))
                entities.append(InverterMonthlyEnergySensor(coordinator, entry, station_id, wn_id, inverter_device_info))
                entities.append(InverterYearlyEnergySensor(coordinator, entry, station_id, wn_id, inverter_device_info))
                entities.append(InverterTotalEnergySensor(coordinator, entry, station_id, wn_id, inverter_device_info))
                entities.append(InverterTemperatureSensor(coordinator, entry, station_id, wn_id, inverter_device_info))
                entities.append(InverterOutputVoltageSensor(coordinator, entry, station_id, wn_id, inverter_device_info))
                entities.append(InverterOutputCurrentSensor(coordinator, entry, station_id, wn_id, inverter_device_info))
                entities.append(InverterOutputFrequencySensor(coordinator, entry, station_id, wn_id, inverter_device_info))
                entities.append(InverterOutputPowerSensor(coordinator, entry, station_id, wn_id, inverter_device_info))
                input_map = [
                    ("inputVoltage", "inputFirElectricity", "inputFirPower", InverterInput1VoltageSensor, InverterInput1CurrentSensor, InverterInput1PowerSensor),
                    ("inputSecVoltage", "inputSecElectricity", "inputSecPower", InverterInput2VoltageSensor, InverterInput2CurrentSensor, InverterInput2PowerSensor),
                    ("inputThirdVoltage", "inputThirdElectricity", "inputThirdPower", InverterInput3VoltageSensor, InverterInput3CurrentSensor, InverterInput3PowerSensor),
                    ("inputFourVoltage", "inputFourElectricity", "inputFourPower", InverterInput4VoltageSensor, InverterInput4CurrentSensor, InverterInput4PowerSensor),
                    ("fiveVolta", "fiveElect", "fivePower", InverterInput5VoltageSensor, InverterInput5CurrentSensor, InverterInput5PowerSensor),
                    ("sixVolta", "sixElect", "sixPower", InverterInput6VoltageSensor, InverterInput6CurrentSensor, InverterInput6PowerSensor),
                ]

                for i, (voltage_key, current_key, power_key, VoltageClass, CurrentClass, PowerClass) in enumerate(input_map):
                    if wn_details.get("wnType", 0) >= i + 1:
                        entities.append(VoltageClass(coordinator, entry, station_id, wn_id, inverter_device_info))
                        entities.append(CurrentClass(coordinator, entry, station_id, wn_id, inverter_device_info))
                        entities.append(PowerClass(coordinator, entry, station_id, wn_id, inverter_device_info))


    async_add_entities(entities)

class StationSensorBase(CoordinatorEntity, SensorEntity):
    """Base class for station sensors."""

    def __init__(self, coordinator, entry, station, name_suffix, key, unit, device_class, state_class):
        super().__init__(coordinator)
        self._station_id = station["id"]
        self._attr_name = f"Power Plant {station['stationName']} {name_suffix}"
        self._attr_unique_id = f"{entry.entry_id}_{station['id']}_{key}"
        self._key = key
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, station["id"])},
            name=f"Power Plant {station['stationName']}",
            manufacturer="Invertechs (Xiamen) Technology Co., Ltd.",
            model="Solar Power Plant",
            model_id=station["id"],
        )

    @property
    def native_value(self):
        for station in self.coordinator.data:
            if station["id"] == self._station_id:
                details = station.get("details", {})
                return details.get(self._key)
        return None

class StationPowerSensor(StationSensorBase):
    def __init__(self, coordinator, entry, station):
        super().__init__(coordinator, entry, station, "Current Power", "power", UnitOfPower.WATT, SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT)

class StationDailyEnergySensor(StationSensorBase):
    def __init__(self, coordinator, entry, station):
        super().__init__(coordinator, entry, station, "Daily Energy", "dayPowerGeneration", UnitOfEnergy.WATT_HOUR, SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING)

class StationMonthlyEnergySensor(StationSensorBase):
    def __init__(self, coordinator, entry, station):
        super().__init__(coordinator, entry, station, "Monthly Energy", "monthPowerGeneration", UnitOfEnergy.WATT_HOUR, SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING)

class StationYearlyEnergySensor(StationSensorBase):
    def __init__(self, coordinator, entry, station):
        super().__init__(coordinator, entry, station, "Yearly Energy", "yearPowerGeneration", UnitOfEnergy.WATT_HOUR, SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING)

class StationTotalEnergySensor(StationSensorBase):
    def __init__(self, coordinator, entry, station):
        super().__init__(coordinator, entry, station, "Total Energy", "totalPowerGeneration", UnitOfEnergy.WATT_HOUR, SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING)

class InverterSensorBase(CoordinatorEntity, SensorEntity):
    """Base class for inverter sensors."""

    def __init__(self, coordinator, entry, station_id, wn_id, device_info, name_suffix, key, unit, device_class, state_class):
        super().__init__(coordinator)
        self._station_id = station_id
        self._wn_id = wn_id
        self._attr_name = f"Inver Energy {device_info['model']} {name_suffix}"
        self._attr_unique_id = f"{entry.entry_id}_{wn_id}_{key}"
        self._key = key
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_device_info = device_info

    @property
    def native_value(self):
        for station in self.coordinator.data:
            if station["id"] == self._station_id:
                for device in station.get("devices", []):
                    if device.get("wnStationVo") and device["wnStationVo"]["wnId"] == self._wn_id:
                        details = device["wnStationVo"].get("details", {})
                        return details.get(self._key)
        return None

class InverterPowerSensor(InverterSensorBase):
    def __init__(self, coordinator, entry, station_id, wn_id, device_info):
        super().__init__(coordinator, entry, station_id, wn_id, device_info, "Power", "power", UnitOfPower.WATT, SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT)

class InverterDailyEnergySensor(InverterSensorBase):
    def __init__(self, coordinator, entry, station_id, wn_id, device_info):
        super().__init__(coordinator, entry, station_id, wn_id, device_info, "Daily Energy", "dayPowerGeneration", UnitOfEnergy.WATT_HOUR, SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING)

class InverterMonthlyEnergySensor(InverterSensorBase):
    def __init__(self, coordinator, entry, station_id, wn_id, device_info):
        super().__init__(coordinator, entry, station_id, wn_id, device_info, "Monthly Energy", "monthPowerGeneration", UnitOfEnergy.WATT_HOUR, SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING)

class InverterYearlyEnergySensor(InverterSensorBase):
    def __init__(self, coordinator, entry, station_id, wn_id, device_info):
        super().__init__(coordinator, entry, station_id, wn_id, device_info, "Yearly Energy", "yearPowerGeneration", UnitOfEnergy.WATT_HOUR, SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING)

class InverterTotalEnergySensor(InverterSensorBase):
    def __init__(self, coordinator, entry, station_id, wn_id, device_info):
        super().__init__(coordinator, entry, station_id, wn_id, device_info, "Total Energy", "totalPowerGeneration", UnitOfEnergy.WATT_HOUR, SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING)

class InverterTemperatureSensor(InverterSensorBase):
    def __init__(self, coordinator, entry, station_id, wn_id, device_info):
        super().__init__(coordinator, entry, station_id, wn_id, device_info, "Temperature", "temp", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT)

class InverterOutputVoltageSensor(InverterSensorBase):
    def __init__(self, coordinator, entry, station_id, wn_id, device_info):
        super().__init__(coordinator, entry, station_id, wn_id, device_info, "Output Voltage", "outputVoltage", UnitOfElectricPotential.VOLT, SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT)

class InverterOutputCurrentSensor(InverterSensorBase):
    def __init__(self, coordinator, entry, station_id, wn_id, device_info):
        super().__init__(coordinator, entry, station_id, wn_id, device_info, "Output Current", "outputElectricity", UnitOfElectricCurrent.AMPERE, SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT)

class InverterOutputFrequencySensor(InverterSensorBase):
    def __init__(self, coordinator, entry, station_id, wn_id, device_info):
        super().__init__(coordinator, entry, station_id, wn_id, device_info, "Output Frequency", "outputFrequency", UnitOfFrequency.HERTZ, SensorDeviceClass.FREQUENCY, SensorStateClass.MEASUREMENT)

class InverterOutputPowerSensor(InverterSensorBase):
    def __init__(self, coordinator, entry, station_id, wn_id, device_info):
        super().__init__(coordinator, entry, station_id, wn_id, device_info, "Output Power", "outputPower", UnitOfPower.WATT, SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT)

class InverterInput1VoltageSensor(InverterSensorBase):
    def __init__(self, coordinator, entry, station_id, wn_id, device_info):
        super().__init__(coordinator, entry, station_id, wn_id, device_info, "Input 1 Voltage", "inputVoltage", UnitOfElectricPotential.VOLT, SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT)

class InverterInput1CurrentSensor(InverterSensorBase):
    def __init__(self, coordinator, entry, station_id, wn_id, device_info):
        super().__init__(coordinator, entry, station_id, wn_id, device_info, "Input 1 Current", "inputFirElectricity", UnitOfElectricCurrent.AMPERE, SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT)

class InverterInput1PowerSensor(InverterSensorBase):
    def __init__(self, coordinator, entry, station_id, wn_id, device_info):
        super().__init__(coordinator, entry, station_id, wn_id, device_info, "Input 1 Power", "inputFirPower", UnitOfPower.WATT, SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT)

class InverterInput2VoltageSensor(InverterSensorBase):
    def __init__(self, coordinator, entry, station_id, wn_id, device_info):
        super().__init__(coordinator, entry, station_id, wn_id, device_info, "Input 2 Voltage", "inputSecVoltage", UnitOfElectricPotential.VOLT, SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT)

class InverterInput2CurrentSensor(InverterSensorBase):
    def __init__(self, coordinator, entry, station_id, wn_id, device_info):
        super().__init__(coordinator, entry, station_id, wn_id, device_info, "Input 2 Current", "inputSecElectricity", UnitOfElectricCurrent.AMPERE, SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT)

class InverterInput2PowerSensor(InverterSensorBase):
    def __init__(self, coordinator, entry, station_id, wn_id, device_info):
        super().__init__(coordinator, entry, station_id, wn_id, device_info, "Input 2 Power", "inputSecPower", UnitOfPower.WATT, SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT)

class InverterInput3VoltageSensor(InverterSensorBase):
    def __init__(self, coordinator, entry, station_id, wn_id, device_info):
        super().__init__(coordinator, entry, station_id, wn_id, device_info, "Input 3 Voltage", "inputThirdVoltage", UnitOfElectricPotential.VOLT, SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT)

class InverterInput3CurrentSensor(InverterSensorBase):
    def __init__(self, coordinator, entry, station_id, wn_id, device_info):
        super().__init__(coordinator, entry, station_id, wn_id, device_info, "Input 3 Current", "inputThirdElectricity", UnitOfElectricCurrent.AMPERE, SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT)

class InverterInput3PowerSensor(InverterSensorBase):
    def __init__(self, coordinator, entry, station_id, wn_id, device_info):
        super().__init__(coordinator, entry, station_id, wn_id, device_info, "Input 3 Power", "inputThirdPower", UnitOfPower.WATT, SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT)

class InverterInput4VoltageSensor(InverterSensorBase):
    def __init__(self, coordinator, entry, station_id, wn_id, device_info):
        super().__init__(coordinator, entry, station_id, wn_id, device_info, "Input 4 Voltage", "inputFourVoltage", UnitOfElectricPotential.VOLT, SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT)

class InverterInput4CurrentSensor(InverterSensorBase):
    def __init__(self, coordinator, entry, station_id, wn_id, device_info):
        super().__init__(coordinator, entry, station_id, wn_id, device_info, "Input 4 Current", "inputFourElectricity", UnitOfElectricCurrent.AMPERE, SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT)

class InverterInput4PowerSensor(InverterSensorBase):
    def __init__(self, coordinator, entry, station_id, wn_id, device_info):
        super().__init__(coordinator, entry, station_id, wn_id, device_info, "Input 4 Power", "inputFourPower", UnitOfPower.WATT, SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT)

class InverterInput5VoltageSensor(InverterSensorBase):
    def __init__(self, coordinator, entry, station_id, wn_id, device_info):
        super().__init__(coordinator, entry, station_id, wn_id, device_info, "Input 5 Voltage", "fiveVolta", UnitOfElectricPotential.VOLT, SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT)

class InverterInput5CurrentSensor(InverterSensorBase):
    def __init__(self, coordinator, entry, station_id, wn_id, device_info):
        super().__init__(coordinator, entry, station_id, wn_id, device_info, "Input 5 Current", "fiveElect", UnitOfElectricCurrent.AMPERE, SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT)

class InverterInput5PowerSensor(InverterSensorBase):
    def __init__(self, coordinator, entry, station_id, wn_id, device_info):
        super().__init__(coordinator, entry, station_id, wn_id, device_info, "Input 5 Power", "fivePower", UnitOfPower.WATT, SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT)

class InverterInput6VoltageSensor(InverterSensorBase):
    def __init__(self, coordinator, entry, station_id, wn_id, device_info):
        super().__init__(coordinator, entry, station_id, wn_id, device_info, "Input 6 Voltage", "sixVolta", UnitOfElectricPotential.VOLT, SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT)

class InverterInput6CurrentSensor(InverterSensorBase):
    def __init__(self, coordinator, entry, station_id, wn_id, device_info):
        super().__init__(coordinator, entry, station_id, wn_id, device_info, "Input 6 Current", "sixElect", UnitOfElectricCurrent.AMPERE, SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT)

class InverterInput6PowerSensor(InverterSensorBase):
    def __init__(self, coordinator, entry, station_id, wn_id, device_info):
        super().__init__(coordinator, entry, station_id, wn_id, device_info, "Input 6 Power", "sixPower", UnitOfPower.WATT, SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT)
