# Monitor your Invertechs Power Plants and Inverters in Home Assistant

Invertechs Power Plants and Inverters are advanced energy systems designed to optimize power generation and usage. This integration allows you to monitor your Invertechs devices directly from Home Assistant.

The integration leverages the Inver Energy App API to communicate with your devices, providing real-time data.

This integration is an initial release. Please report any issues or provide feedback to help improve the integration. Thank you for your support!

## Features
* This integration uses the API to gather the data. It does not work locally. Credentials are required to access the API. It is queried with 5-minute intervals.
* Each power plant is a separate device with sensors and diagnostic indicators. The "Status" indicator provides some extra attributes.
* Each inverter is connected to a power plant and created as a separate device with its own sensors and indicators. The "Status" indicator provides some extra attributes.

## Installation

### Using [HACS](https://hacs.xyz/) (recommended)

1. Add the custom repository:

   [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=mpedziwiatr02&repository=Invertechs-Integration)
2. Restart Home Assistant.
3. Add the integration:

   [![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=invertechs)
4. Follow the configuration steps. You'll need to provide your e-mail address and password. The integration will discover the devices associated with your account.

### Manual installation
1. Copy the folder named `invertechs` from the [latest release](https://github.com/mpedziwiatr02/invertechs-integration/releases/latest) to the `custom_components` folder.
2. Restart Home Assistant.
3. Add the integration:

   [![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=invertechs)
4. Follow the configuration steps. You'll need to provide your e-mail address and password. The integration will discover the devices associated with your account.

## Tested devices
* IS-050S
* IS-080S

## Disclaimer

This project is not in any way associated with or related to Invertechs (Xiamen) Technology Co., Ltd. The information here and online is for educational and resource purposes only and therefore the developers do not endorse or condone any inappropriate use of it, and take no legal responsibility for the functionality or security of your devices.
