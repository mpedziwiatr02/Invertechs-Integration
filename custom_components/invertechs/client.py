import aiohttp, logging

_LOGGER = logging.getLogger(__name__)

class InvertechsClient:
    def __init__(self, email: str, password: str, session: aiohttp.ClientSession):
        self.email = email
        self.password = password
        self.session = session
        self.token = None
        self.user_data = None
        self.base_url = "https://appeu.invertechs.com/cniotapi/app/"
        self.headers = {
            "App-Type": "Inver",
            "Lang-Type": "en_US",
            "Content-Type": "application/json",
        }

    async def login(self) -> bool:
        url = self.base_url + "user/login"
        data = {
            "mail": self.email,
            "password": self.password,
            "mailCode": "",
            "emailOrPhone": 0
        }
        async with self.session.post(url, json=data, headers=self.headers) as resp:
            if resp.status == 200:
                js = await resp.json()
                if js.get("code") == 200:
                    self.token = js["data"]["token"]
                    self.user_data = js["data"]
                    return True
                _LOGGER.error("Login failed with status %s", resp.status)
        return False

    async def logout(self) -> bool:
        if not self.token:
            return True
        
        url = self.base_url + "user/logout"
        headers = {**self.headers, "Authorization": self.token}
        async with self.session.post(url, headers=headers) as resp:
            if resp.status == 200:
                js = await resp.json()
                if js.get("code") == 200:
                    self.token = None
                    return True
                _LOGGER.error("Logout failed with status %s", resp.status)
        return False

    async def get_stations(self):
        if not self.token:
            if not await self.login():
                return []
        
        url = self.base_url + "station/UI2Page"
        data = {
            "searchValue": None,
            "collected": 0,
            "sortType": 0,
            "status": 0,
            "stationType": None,
            "existsOwner": None,
            "queryQo": {"pageNum": 1, "pageSize": 10}
        }
        headers = {**self.headers, "Authorization": self.token}
        async with self.session.post(url, json=data, headers=headers) as resp:
            if resp.status == 200:
                js = await resp.json()
                if js.get("code") == 200:
                    return js.get("rows", [])
                _LOGGER.error("Failed to fetch stations list with status %s", resp.status)
        return []

    async def get_station_details(self, station_id: str):
        if not self.token:
            if not await self.login():
                return {}
        
        url = self.base_url + "station/getStationDataDetails"
        data = {"stationId": station_id}
        headers = {**self.headers, "Authorization": self.token}
        async with self.session.post(url, json=data, headers=headers) as resp:
            if resp.status == 200:
                js = await resp.json()
                if js.get("code") == 200:
                    return js.get("data", {})
                _LOGGER.error("Failed to fetch station data details with status %s", resp.status)
        return {}

    async def get_devices_in_station(self, station_id: str):
        if not self.token:
            if not await self.login():
                return {}
        
        url = self.base_url + "station/getDevicesListInsideStation"
        data = {
            "queryQo": {"pageNum": 1, "pageSize": 10},
            "searchType": None,
            "powerStationId": station_id
        }
        headers = {**self.headers, "Authorization": self.token}
        async with self.session.post(url, json=data, headers=headers) as resp:
            if resp.status == 200:
                js = await resp.json()
                if js.get("code") == 200:
                    return js
                _LOGGER.error("Failed to fetch devices list inside station with status %s", resp.status)
        return {}

    async def get_inverter_details(self, wn_id: str, station_id: str):
        if not self.token:
            if not await self.login():
                return {}
        
        url = self.base_url + "wnData/getWnDataDetails"
        data = {"wnId": wn_id, "stationId": station_id}
        headers = {**self.headers, "Authorization": self.token}
        async with self.session.post(url, json=data, headers=headers) as resp:
            if resp.status == 200:
                js = await resp.json()
                if js.get("code") == 200:
                    return js.get("data", {})
                _LOGGER.error("Failed to fetch inverter data details with status %s", resp.status)
        return {}