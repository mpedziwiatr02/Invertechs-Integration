import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.const import CONF_PASSWORD, CONF_EMAIL

from .client import (
    InvertechsApiError,
    InvertechsAuthError,
    InvertechsClient,
    InvertechsConnectionError,
    InvertechsError,
)
from .const import (
    CONF_REGION,
    CONFIG_ENTRY_VERSION,
    DEFAULT_REGION,
    DEVICE_UPDATE_INTERVAL,
    DOMAIN,
    FAST_UPDATE_INTERVAL,
)
from .coordinator_data import fetch_fast_power_plants, fetch_full_power_plants
from .polling import (
    mark_device_offline_snapshot,
    should_reduce_device_polling,
    should_reduce_fast_polling,
    update_polling_after_fast,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "binary_sensor", "number"]


def _config_entry_region(entry: ConfigEntry) -> str:
    return entry.options.get(CONF_REGION, entry.data.get(CONF_REGION, DEFAULT_REGION))


def _create_client(entry: ConfigEntry, session) -> InvertechsClient:
    return InvertechsClient(
        entry.data[CONF_EMAIL],
        entry.data[CONF_PASSWORD],
        session,
        region=_config_entry_region(entry),
    )


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate config entries to the latest version."""
    if config_entry.version >= CONFIG_ENTRY_VERSION:
        return True

    data = dict(config_entry.data)
    if CONF_REGION not in data:
        data[CONF_REGION] = DEFAULT_REGION

    email = data[CONF_EMAIL].lower()
    region = data[CONF_REGION]
    hass.config_entries.async_update_entry(
        config_entry,
        data=data,
        unique_id=f"{email}_{region}",
        version=CONFIG_ENTRY_VERSION,
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = aiohttp_client.async_get_clientsession(hass)
    client = _create_client(entry, session)

    if not await client.login():
        _LOGGER.error("Failed to login to Invertechs API (%s)", _config_entry_region(entry))
        return False

    entry_data: dict = {
        "client": client,
        "cached_fast_data": None,
        "cached_device_data": None,
        "reduced_polling": False,
        "inverters_online": True,
        "offline_fast_snapshot_taken": False,
        "offline_device_snapshot_taken": False,
    }

    async def async_update_fast():
        try:
            plants = await fetch_fast_power_plants(
                client,
                entry_data.get("cached_fast_data"),
                reduced_polling=should_reduce_fast_polling(entry_data),
            )
        except InvertechsAuthError as err:
            raise ConfigEntryAuthFailed(f"Authentication failed: {err}") from err
        except (InvertechsConnectionError, InvertechsApiError, InvertechsError) as err:
            raise UpdateFailed(f"Error fetching live power plant data: {err}") from err
        entry_data["cached_fast_data"] = plants
        update_polling_after_fast(
            entry_data, fast_coordinator, device_coordinator, plants
        )
        return plants

    async def async_update_devices():
        reduced_polling = should_reduce_device_polling(entry_data)
        try:
            plants = await fetch_full_power_plants(
                client,
                entry_data.get("cached_device_data"),
                reduced_polling=reduced_polling,
            )
        except InvertechsAuthError as err:
            raise ConfigEntryAuthFailed(f"Authentication failed: {err}") from err
        except (InvertechsConnectionError, InvertechsApiError, InvertechsError) as err:
            raise UpdateFailed(f"Error fetching device data: {err}") from err
        if not reduced_polling:
            entry_data["cached_device_data"] = plants
            mark_device_offline_snapshot(entry_data)
        return plants

    fast_coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"{DOMAIN}_fast",
        update_method=async_update_fast,
        update_interval=FAST_UPDATE_INTERVAL,
    )

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"{DOMAIN}_devices",
        update_method=async_update_devices,
        update_interval=DEVICE_UPDATE_INTERVAL,
    )

    device_coordinator = coordinator

    await fast_coordinator.async_config_entry_first_refresh()
    await device_coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    entry_data["coordinator"] = device_coordinator
    entry_data["fast_coordinator"] = fast_coordinator
    entry_data["power_plant_coordinator"] = fast_coordinator
    hass.data[DOMAIN][entry.entry_id] = entry_data

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await hass.data[DOMAIN][entry.entry_id]["client"].logout()
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
