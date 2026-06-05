# Monitor your Invertechs Power Plants and Inverters in Home Assistant

Invertechs Power Plants and Inverters are advanced energy systems designed to optimize power generation and usage. This integration allows you to monitor your Invertechs devices directly from Home Assistant.

The integration leverages the Inver Energy App API to communicate with your devices, providing periodically updated data.

Please report any issues or provide feedback to help improve the integration. Thank you for your support!

## Features
* This integration uses the API to gather the data. It does not work locally. Credentials are required to access the API. While inverters are online, power plant metrics and power limits are refreshed every 30 seconds; when all inverters are offline, polling is reduced to every 5 minutes (IoT probe for connection only). Inverter detail readings are refreshed every 5 minutes while online and paused when offline.
* Inverter **Power limit** is exposed as a number entity (2–100 %) and can be changed when the device is online.
* Each power plant is a separate device with sensors and diagnostic indicators. The "Status" indicator provides some extra attributes.
* Each inverter is connected to a power plant and created as a separate device with its own sensors and indicators. The "Status" indicator provides some extra attributes.

## Installation

### Using [HACS](https://hacs.xyz/) (recommended)

1. Add the custom repository:

   [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=mpedziwiatr02&repository=Invertechs-Integration)
2. Restart Home Assistant.
3. Add the integration:

   [![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=invertechs)
4. Follow the configuration steps. You'll need to provide your e-mail address, password, and server region (Europe or China). The integration will discover the devices associated with your account.

### Manual installation
1. Copy the folder named `invertechs` from the [latest release](https://github.com/mpedziwiatr02/invertechs-integration/releases/latest) to the `custom_components` folder.
2. Restart Home Assistant.
3. Add the integration:

   [![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=invertechs)
4. Follow the configuration steps. You'll need to provide your e-mail address, password, and server region (Europe or China). The integration will discover the devices associated with your account.

## API endpoints and entities

Base URL: `https://appeu.invertechs.com/cniotapi/` (Europe) or `https://appcn.invertechs.com/cniotapi/` (China).

### Authentication

| API endpoint | When called | Purpose |
|--------------|-------------|---------|
| `app/user/login` | On setup / re-auth | Signs in and stores an API session token used for later requests |
| `app/user/logout` | When the integration is removed | Ends the API session on the server; does not create or update any Home Assistant entities |

### Power plant

| API endpoint | Poll schedule | Entities / data |
|--------------|---------------|-----------------|
| `app/station/UI2Page` | Fast (30 s online) / Device (5 min online)<br>Skipped offline (cached list) | Station list (discovery) |
| `app/station/getStationDataDetails` | Device (first fetch, if needed) | One-time station metadata; ongoing sensor values come from `refreshStationDataDetails` |
| `app/station/refreshStationDataDetails` | Fast (30 s online, 5 min offline) | Current power, daily/monthly/yearly/total energy, Connection, Status |

### Inverter

| API endpoint | Poll schedule | Entities / data |
|--------------|---------------|-----------------|
| `app/station/getDevicesListInsideStation` | Device (5 min online) | Inverter list (discovery) |
| `iot/station/getStationWnPowerInfo` | Fast (30 s online, 5 min offline probe) | Connection<br>Power limit (read) |
| `app/wn/editPowerPercent` | On user action | Power limit (write) |
| `app/wnData/getWnDataDetails` | Device (5 min online) | Current power, daily/monthly/yearly/total energy, temperature, output voltage/current/frequency/power, DC input sensors, Status (alarm) |

When all inverters are offline, fast polling uses cached plant data plus `refreshStationDataDetails` and an IoT probe; device detail fetches are paused until an inverter is online again.

## Tested devices
* IS-050S
* IS-080S

## Disclaimer

This project is not in any way associated with or related to Invertechs (Xiamen) Technology Co., Ltd. The information here and online is for educational and resource purposes only and therefore the developers do not endorse or condone any inappropriate use of it, and take no legal responsibility for the functionality or security of your devices.

Parts of this project, including code and documentation, were created or refined with the assistance of AI tools. AI-generated output may contain errors or omissions. Review, test, and verify changes before relying on them in production.
