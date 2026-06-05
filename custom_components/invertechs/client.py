"""Invertechs cloud API client."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .const import (
    API_AUTH_ERROR_CODES,
    API_BASE_URLS,
    API_PAGE_SIZE,
    API_SUCCESS_CODE,
    API_TIMEOUT,
    DEFAULT_REGION,
    POWER_LIMIT_PARAM_CODE,
)

_LOGGER = logging.getLogger(__name__)


class InvertechsError(Exception):
    """Base exception for Invertechs client errors."""


class InvertechsConnectionError(InvertechsError):
    """Raised when the API cannot be reached."""


class InvertechsAuthError(InvertechsError):
    """Raised when authentication fails."""


class InvertechsApiError(InvertechsError):
    """Raised when the API returns an error response."""

    def __init__(self, message: str, *, code: int | None = None) -> None:
        super().__init__(message)
        self.code = code


class InvertechsClient:
    """Client for the Invertechs cloud API."""

    def __init__(
        self,
        email: str,
        password: str,
        session: aiohttp.ClientSession,
        region: str = DEFAULT_REGION,
    ) -> None:
        self.email = email
        self.password = password
        self.session = session
        self.region = region if region in API_BASE_URLS else DEFAULT_REGION
        self.token: str | None = None
        self.user_data: dict[str, Any] | None = None
        self.base_url = API_BASE_URLS[self.region]
        self.headers = {
            "App-Type": "Inver",
            "Lang-Type": "en_US",
            "Content-Type": "application/json",
        }

    async def login(self) -> bool:
        """Authenticate and store the session token."""
        try:
            await self._authenticate()
            return True
        except InvertechsAuthError:
            return False

    async def logout(self) -> bool:
        """Invalidate the session token."""
        if not self.token:
            return True

        try:
            await self._post("app/user/logout", auth=True)
            self.token = None
            return True
        except InvertechsError as err:
            _LOGGER.warning("Logout failed: %s", err)
            self.token = None
            return False

    async def get_stations(self) -> list[dict[str, Any]]:
        """Return all power plants from the station API."""
        return await self._fetch_paginated_rows(
            "app/station/UI2Page",
            {
                "searchValue": None,
                "collected": 0,
                "sortType": 0,
                "status": 0,
                "stationType": None,
                "existsOwner": None,
            },
        )

    async def get_station_details(self, station_id: str) -> dict[str, Any]:
        """Return power plant details (API stationId)."""
        return await self._post(
            "app/station/getStationDataDetails",
            {"stationId": station_id},
            auth=True,
            data_key="data",
        )

    async def refresh_station_details(self, station_id: str) -> dict[str, Any]:
        """Return refreshed live plant metrics (used by the mobile app overview)."""
        return await self._post(
            "app/station/refreshStationDataDetails",
            {"stationId": station_id},
            auth=True,
            data_key="data",
        )

    async def get_station_wn_power_info(self, station_id: str) -> dict[str, Any]:
        """Return live inverter power and limit data for a power plant."""
        return await self._post(
            "iot/station/getStationWnPowerInfo",
            {"id": station_id},
            auth=True,
            data_key="data",
        )

    async def get_devices_in_station(self, station_id: str) -> list[dict[str, Any]]:
        """Return all devices inside a power plant (API powerStationId)."""
        return await self._fetch_paginated_rows(
            "app/station/getDevicesListInsideStation",
            {
                "searchType": None,
                "powerStationId": station_id,
            },
        )

    async def get_inverter_details(self, wn_id: str, station_id: str) -> dict[str, Any]:
        """Return inverter details (API wnId / stationId)."""
        return await self._post(
            "app/wnData/getWnDataDetails",
            {"wnId": wn_id, "stationId": station_id},
            auth=True,
            data_key="data",
        )

    async def set_inverter_power_percent(self, wn_id: str, percent: float) -> None:
        """Set the inverter active power limit as a percentage."""
        await self._post(
            "app/wn/editPowerPercent",
            {"wnId": wn_id, "paramValue": percent},
            auth=True,
        )

    @staticmethod
    def get_inverter_power_limit_percent(
        live_data: dict[str, Any] | None, wn_id: str
    ) -> float | None:
        """Read power limit percent from live IoT payload (param code 72)."""
        if not live_data:
            return None
        for param in live_data.get("iotWnParams", []):
            if (
                param.get("wnId") == wn_id
                and str(param.get("paramCode")) == POWER_LIMIT_PARAM_CODE
            ):
                value = param.get("paramValue")
                return float(value) if value is not None else None
        return None

    async def _authenticate(self) -> None:
        """Log in and set the token."""
        self.token = None
        data = await self._post(
            "app/user/login",
            {
                "mail": self.email,
                "password": self.password,
                "mailCode": "",
                "emailOrPhone": 0,
            },
            auth=False,
            data_key="data",
            allow_retry=False,
        )
        if not isinstance(data, dict) or not data.get("token"):
            raise InvertechsAuthError("Login response did not include a token")
        self.token = data["token"]
        self.user_data = data

    async def _ensure_token(self) -> None:
        if not self.token:
            await self._authenticate()

    async def _fetch_paginated_rows(
        self,
        path: str,
        payload: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Fetch all pages of a list endpoint."""
        rows: list[dict[str, Any]] = []
        page_num = 1

        while True:
            page_payload = {
                **payload,
                "queryQo": {"pageNum": page_num, "pageSize": API_PAGE_SIZE},
            }
            response = await self._post(path, page_payload, auth=True)
            if not isinstance(response, dict):
                raise InvertechsApiError(f"Unexpected paginated response for {path}")

            page_rows = response.get("rows", [])
            if not isinstance(page_rows, list):
                raise InvertechsApiError(f"Unexpected rows payload for {path}")

            rows.extend(page_rows)

            total = response.get("total")
            if isinstance(total, int) and len(rows) >= total:
                break
            if len(page_rows) < API_PAGE_SIZE:
                break

            page_num += 1

        return rows

    async def _post(
        self,
        path: str,
        payload: dict[str, Any],
        *,
        auth: bool,
        data_key: str | None = None,
        allow_retry: bool = True,
    ) -> Any:
        """POST to the API with optional auth retry."""
        if auth:
            await self._ensure_token()

        for attempt in range(2):
            try:
                body = await self._request(path, payload, auth=auth)
            except InvertechsAuthError:
                if not allow_retry or attempt == 1:
                    raise
                self.token = None
                await self._authenticate()
                continue

            api_code = body.get("code")
            if api_code == API_SUCCESS_CODE:
                if data_key is None:
                    return body
                return body.get(data_key, {})

            if (
                auth
                and allow_retry
                and attempt == 0
                and api_code in API_AUTH_ERROR_CODES
            ):
                _LOGGER.debug("API auth error (code %s), re-authenticating", api_code)
                self.token = None
                await self._authenticate()
                continue

            message = body.get("msg") or body.get("message") or "Unknown API error"
            if api_code in API_AUTH_ERROR_CODES:
                raise InvertechsAuthError(f"{message} (code {api_code})")
            raise InvertechsApiError(f"{message} (code {api_code})", code=api_code)

        raise InvertechsAuthError("Authentication failed after retry")

    async def _request(
        self,
        path: str,
        payload: dict[str, Any],
        *,
        auth: bool,
    ) -> dict[str, Any]:
        """Execute an HTTP POST and return the parsed JSON body."""
        url = f"{self.base_url}{path}"
        headers = dict(self.headers)
        if auth and self.token:
            headers["Authorization"] = self.token

        try:
            async with self.session.post(
                url,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=API_TIMEOUT),
            ) as response:
                if response.status in {401, 403}:
                    raise InvertechsAuthError(
                        f"HTTP {response.status} from Invertechs API"
                    )
                if response.status >= 400:
                    raise InvertechsConnectionError(
                        f"HTTP {response.status} from Invertechs API"
                    )
                try:
                    body = await response.json()
                except aiohttp.ContentTypeError as err:
                    raise InvertechsConnectionError(
                        "Invalid response from Invertechs API"
                    ) from err
        except aiohttp.ClientError as err:
            raise InvertechsConnectionError(
                f"Could not connect to Invertechs API: {err}"
            ) from err

        if not isinstance(body, dict):
            raise InvertechsApiError("Unexpected API response format")

        return body
