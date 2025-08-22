import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.const import CONF_PASSWORD, CONF_EMAIL

from .client import InvertechsClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "binary_sensor"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    email = entry.data[CONF_EMAIL]
    password = entry.data[CONF_PASSWORD]
    
    session = aiohttp_client.async_get_clientsession(hass)
    client = InvertechsClient(email, password, session)
    
    login_data = await client.login()
    if not login_data:
        _LOGGER.error("Failed to login to Invertechs API")
        return False
    
    async def async_update_data():
        try:
            stations = await client.get_stations()
            for station in stations:
                station_id = station["id"]
                station["details"] = await client.get_station_details(station_id)
                devices_data = await client.get_devices_in_station(station_id)
                station["devices"] = devices_data.get("rows", [])
                for device in station["devices"]:
                    if device.get("devicesType") == 0 and device.get("wnStationVo"):
                        wn = device["wnStationVo"]
                        wn["details"] = await client.get_inverter_details(wn["wnId"], station_id)
            return stations
        except Exception as err:
            raise UpdateFailed(f"Error fetching data: {err}")
    
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=async_update_data,
        update_interval=timedelta(minutes=5),
    )
    
    await coordinator.async_config_entry_first_refresh()
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
    }
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await hass.data[DOMAIN][entry.entry_id]["client"].logout()
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok