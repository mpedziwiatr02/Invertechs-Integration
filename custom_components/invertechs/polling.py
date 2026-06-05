"""Adaptive polling intervals based on inverter connectivity."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import FAST_UPDATE_INTERVAL, OFFLINE_UPDATE_INTERVAL
from .entity import account_inverters_are_online

_LOGGER = logging.getLogger(__name__)


def should_reduce_fast_polling(entry_data: dict[str, Any]) -> bool:
    """Return True when the fast coordinator should use offline sleep mode."""
    if entry_data.get("inverters_online", True):
        return False
    return entry_data.get("offline_fast_snapshot_taken", False)


def should_reduce_device_polling(entry_data: dict[str, Any]) -> bool:
    """Return True when the device coordinator should use offline sleep mode."""
    if entry_data.get("inverters_online", True):
        return False
    return entry_data.get("offline_device_snapshot_taken", False)


def update_polling_after_fast(
    entry_data: dict[str, Any],
    fast_coordinator: DataUpdateCoordinator,
    device_coordinator: DataUpdateCoordinator,
    power_plants: list[dict[str, Any]],
) -> None:
    """Adjust polling state after a fast coordinator refresh."""
    now_online = account_inverters_are_online(power_plants)
    was_online = entry_data.get("inverters_online", True)

    if now_online:
        entry_data["inverters_online"] = True
        entry_data["offline_fast_snapshot_taken"] = False
        entry_data["offline_device_snapshot_taken"] = False
        entry_data["reduced_polling"] = False
        fast_interval = FAST_UPDATE_INTERVAL
    else:
        entry_data["inverters_online"] = False
        if was_online:
            _LOGGER.debug(
                "Inverters went offline; keeping full polling for one final snapshot"
            )
            entry_data["offline_fast_snapshot_taken"] = True
            entry_data["offline_device_snapshot_taken"] = False
            device_coordinator.async_request_refresh()
        elif not entry_data.get("offline_fast_snapshot_taken", False):
            entry_data["offline_fast_snapshot_taken"] = True

        entry_data["reduced_polling"] = (
            entry_data.get("offline_fast_snapshot_taken", False)
            and entry_data.get("offline_device_snapshot_taken", False)
        )
        fast_interval = OFFLINE_UPDATE_INTERVAL

    if fast_coordinator.update_interval != fast_interval:
        fast_coordinator.update_interval = fast_interval
        _LOGGER.debug(
            "Fast polling interval set to %s (inverters_online=%s)",
            fast_interval,
            now_online,
        )


def mark_device_offline_snapshot(entry_data: dict[str, Any]) -> None:
    """Mark the final device detail fetch complete after going offline."""
    if entry_data.get("inverters_online", True):
        return

    entry_data["offline_device_snapshot_taken"] = True
    entry_data["reduced_polling"] = entry_data.get("offline_fast_snapshot_taken", False)
    _LOGGER.debug("Offline device snapshot complete; device polling paused")
