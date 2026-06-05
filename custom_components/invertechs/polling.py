"""Adaptive polling intervals based on inverter connectivity."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, FAST_UPDATE_INTERVAL, OFFLINE_UPDATE_INTERVAL
from .entity import account_inverters_are_online

_LOGGER = logging.getLogger(__name__)


def apply_polling_mode(
    entry_data: dict[str, Any],
    fast_coordinator: DataUpdateCoordinator,
    power_plants: list[dict[str, Any]],
) -> bool:
    """Adjust coordinator intervals from inverter online state. Returns reduced_polling flag."""
    inverters_online = account_inverters_are_online(power_plants)
    reduced_polling = not inverters_online

    entry_data["inverters_online"] = inverters_online
    entry_data["reduced_polling"] = reduced_polling

    fast_interval = FAST_UPDATE_INTERVAL if inverters_online else OFFLINE_UPDATE_INTERVAL
    if fast_coordinator.update_interval != fast_interval:
        fast_coordinator.update_interval = fast_interval
        _LOGGER.debug(
            "Fast polling interval set to %s (inverters_online=%s)",
            fast_interval,
            inverters_online,
        )

    return reduced_polling
