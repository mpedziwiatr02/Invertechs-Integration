from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up the Invertechs binary sensors."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]

    entities = []

    for station in coordinator.data:
        station_id = station["id"]
        station_name = station["stationName"]

        # Station binary sensors
        entities.append(StationOnlineBinarySensor(coordinator, entry, station))
        entities.append(StationAlarmBinarySensor(coordinator, entry, station))

        # Inverter binary sensors
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

                entities.append(InverterOnlineBinarySensor(coordinator, entry, station_id, wn_id, inverter_device_info))
                entities.append(InverterAlarmBinarySensor(coordinator, entry, station_id, wn_id, inverter_device_info))

    async_add_entities(entities)

class StationBinarySensorBase(CoordinatorEntity, BinarySensorEntity):
    """Base class for station binary sensors."""

    def __init__(self, coordinator, entry, station, name_suffix, key, entity_category, device_class, on_value):
        super().__init__(coordinator)
        self._station_id = station["id"]
        self._attr_name = f"Power Plant {station['stationName']} {name_suffix}"
        self._attr_unique_id = f"{entry.entry_id}_{station['id']}_{key}"
        self._key = key
        self._attr_entity_category = entity_category
        self._attr_device_class = device_class
        self._on_value = on_value
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, station["id"])},
            name=f"Power Plant {station['stationName']}",
            manufacturer="Invertechs (Xiamen) Technology Co., Ltd.",
            model="Solar Power Plant",
            model_id=station["id"],
        )

    @property
    def is_on(self):
        for station in self.coordinator.data:
            if station["id"] == self._station_id:
                details = station.get("details", {})
                val = details.get(self._key, station.get(self._key))
                return val == self._on_value if val is not None else False
        return False

class StationOnlineBinarySensor(StationBinarySensorBase):
    def __init__(self, coordinator, entry, station):
        super().__init__(coordinator, entry, station, "Connection", "stationOnlineStatus", EntityCategory.DIAGNOSTIC, BinarySensorDeviceClass.CONNECTIVITY, True)

class StationAlarmBinarySensor(StationBinarySensorBase):
    def __init__(self, coordinator, entry, station):
        super().__init__(coordinator, entry, station, "Status", "isHaveAlarm", EntityCategory.DIAGNOSTIC, BinarySensorDeviceClass.PROBLEM, 1)

    @property
    def extra_state_attributes(self):
        for station in self.coordinator.data:
            if station["id"] == self._station_id:
                return {
                    "creation_time": station.get("createTime"),
                    "plant_address": station.get("stationAddress"),
                    "capacity": station.get("capacity"),
                    "inverters_count": station.get("wnNum"),
                    "meter_exists": True if station.get("existsMeter") else False,
                    "battery_exists": True if station.get("existsBattery") else False,
                }
        return None

class InverterBinarySensorBase(CoordinatorEntity, BinarySensorEntity):
    """Base class for inverter binary sensors."""

    def __init__(self, coordinator, entry, station_id, wn_id, device_info, name_suffix, key, entity_category, device_class, on_value):
        super().__init__(coordinator)
        self._station_id = station_id
        self._wn_id = wn_id
        self._attr_name = f"Inver Energy {device_info['model']} {name_suffix}"
        self._attr_unique_id = f"{entry.entry_id}_{wn_id}_{key}"
        self._key = key
        self._attr_entity_category = entity_category
        self._attr_device_class = device_class
        self._on_value = on_value
        self._attr_device_info = device_info

    @property
    def is_on(self):
        for station in self.coordinator.data:
            if station["id"] == self._station_id:
                for device in station.get("devices", []):
                    if device.get("wnStationVo") and device["wnStationVo"]["wnId"] == self._wn_id:
                        wn = device["wnStationVo"]
                        details = wn.get("details", {})
                        val = details.get(self._key, wn.get(self._key))
                        return val == self._on_value if val is not None else False
        return False

class InverterOnlineBinarySensor(InverterBinarySensorBase):
    def __init__(self, coordinator, entry, station_id, wn_id, device_info):
        super().__init__(coordinator, entry, station_id, wn_id, device_info, "Connection", "onlineStatus", EntityCategory.DIAGNOSTIC, BinarySensorDeviceClass.CONNECTIVITY, True)

class InverterAlarmBinarySensor(InverterBinarySensorBase):
    def __init__(self, coordinator, entry, station_id, wn_id, device_info):
        super().__init__(coordinator, entry, station_id, wn_id, device_info, "Status", "alarmStatus", EntityCategory.DIAGNOSTIC, BinarySensorDeviceClass.PROBLEM, True)

    @property
    def extra_state_attributes(self):
        for station in self.coordinator.data:
            if station["id"] == self._station_id:
                for device in station.get("devices", []):
                    wn = device.get("wnStationVo")
                    if wn and device["wnStationVo"]["wnId"] == self._wn_id:
                        details = wn.get("details", {})
                        return {
                            "plant_name": details.get("stationName"),
                            "production_month": wn.get("pdMonth", "")[:-2] + "-" + wn.get("pdMonth", "")[-2:] if wn.get("pdMonth") else "",
                            "valid_thru": wn.get("validDate"),
                            "rated_power": details.get("ratedPower"),
                            "inverter_type": details.get("wnType"),
                        }
        return None