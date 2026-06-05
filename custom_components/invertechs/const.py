from datetime import timedelta

DOMAIN = "invertechs"

CONF_REGION = "region"

REGION_EU = "eu"
REGION_CN = "cn"
DEFAULT_REGION = REGION_EU

CONFIG_ENTRY_VERSION = 2

API_BASE_URLS = {
    REGION_EU: "https://appeu.invertechs.com/cniotapi/",
    REGION_CN: "https://appcn.invertechs.com/cniotapi/",
}

API_TIMEOUT = 30
API_PAGE_SIZE = 100
API_SUCCESS_CODE = 200
API_AUTH_ERROR_CODES = frozenset({401, 403})

# App polling: getStationWnPowerInfo ~every 2–12 s; refreshStationDataDetails on overview.
FAST_UPDATE_INTERVAL = timedelta(seconds=30)
OFFLINE_UPDATE_INTERVAL = timedelta(minutes=5)
DEVICE_UPDATE_INTERVAL = timedelta(minutes=5)

POWER_LIMIT_PARAM_CODE = "72"
POWER_LIMIT_MIN_PERCENT = 2
POWER_LIMIT_MAX_PERCENT = 100
