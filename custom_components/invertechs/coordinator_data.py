"""Coordinator data refresh helpers."""

from __future__ import annotations

import copy
import logging
from typing import Any

from .client import InvertechsClient, InvertechsError
from .entity import DEVICE_TYPE_INVERTER

_LOGGER = logging.getLogger(__name__)


async def fetch_fast_power_plants(
    client: InvertechsClient,
    cached_plants: list[dict[str, Any]] | None,
    *,
    reduced_polling: bool,
) -> list[dict[str, Any]]:
    """Fetch plant metrics; use reduced polling when inverters are offline."""
    cached_by_id = {plant["id"]: plant for plant in cached_plants or []}

    if reduced_polling and cached_plants:
        power_plants = copy.deepcopy(cached_plants)
    else:
        power_plants = await client.get_stations()

    for power_plant in power_plants:
        station_id = power_plant["id"]
        cached_plant = cached_by_id.get(station_id)

        if reduced_polling:
            # Plant connection and current power from refresh; inverter connection from IoT probe.
            power_plant["details"] = await client.refresh_station_details(station_id)
            power_plant["live"] = await _fetch_live_or_cache(
                client, station_id, cached_plant
            )
        else:
            power_plant["details"] = await client.refresh_station_details(station_id)
            power_plant["live"] = await client.get_station_wn_power_info(station_id)

    return power_plants


async def _fetch_live_or_cache(
    client: InvertechsClient,
    station_id: str,
    cached_plant: dict[str, Any] | None,
) -> dict[str, Any]:
    """Probe IoT for inverter connection; reuse cache when the inverter is unreachable."""
    try:
        return await client.get_station_wn_power_info(station_id)
    except InvertechsError as err:
        _LOGGER.debug(
            "IoT probe failed for station %s (%s), using cached live data",
            station_id,
            err,
        )
        if cached_plant:
            live = cached_plant.get("live")
            if isinstance(live, dict):
                return live
        return {}


async def fetch_full_power_plants(
    client: InvertechsClient,
    cached_plants: list[dict[str, Any]] | None,
    *,
    reduced_polling: bool,
) -> list[dict[str, Any]]:
    """Fetch power plants with devices and inverter details."""
    if reduced_polling:
        if cached_plants:
            return copy.deepcopy(cached_plants)
        _LOGGER.debug("Skipping device detail fetch while inverters are offline (no cache)")

    power_plants = await client.get_stations()
    for power_plant in power_plants:
        await _refresh_power_plant(client, power_plant, cached_plant=None)
    return power_plants


async def _refresh_power_plant(
    client: InvertechsClient,
    power_plant: dict[str, Any],
    cached_plant: dict[str, Any] | None,
) -> None:
    """Load devices and inverter details for one power plant."""
    power_plant_id = power_plant["id"]
    if "details" not in power_plant:
        power_plant["details"] = await client.get_station_details(power_plant_id)

    cached_details_by_wn: dict[str, dict[str, Any]] = {}
    if cached_plant:
        for device in cached_plant.get("devices", []):
            if device.get("devicesType") == DEVICE_TYPE_INVERTER and device.get("wnStationVo"):
                wn = device["wnStationVo"]
                if wn.get("details"):
                    cached_details_by_wn[wn["wnId"]] = wn["details"]

    power_plant["devices"] = await client.get_devices_in_station(power_plant_id)
    for device in power_plant["devices"]:
        if device.get("devicesType") != DEVICE_TYPE_INVERTER or not device.get("wnStationVo"):
            continue
        wn = device["wnStationVo"]
        wn_id = wn["wnId"]
        if wn_id in cached_details_by_wn:
            wn["details"] = cached_details_by_wn[wn_id]
        else:
            wn["details"] = await client.get_inverter_details(wn_id, power_plant_id)
