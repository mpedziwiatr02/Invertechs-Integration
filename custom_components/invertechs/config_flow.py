from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import aiohttp_client, selector
from homeassistant.const import CONF_PASSWORD, CONF_EMAIL

from .client import (
    InvertechsAuthError,
    InvertechsClient,
    InvertechsConnectionError,
    InvertechsError,
)
from .const import (
    CONF_REGION,
    CONFIG_ENTRY_VERSION,
    DEFAULT_REGION,
    DOMAIN,
    REGION_CN,
    REGION_EU,
)


def _entry_unique_id(email: str, region: str) -> str:
    return f"{email.lower()}_{region}"


class InvertechsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Invertechs."""

    VERSION = CONFIG_ENTRY_VERSION

    @staticmethod
    @config_entries.callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "InvertechsOptionsFlowHandler":
        return InvertechsOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            email = user_input[CONF_EMAIL]
            password = user_input[CONF_PASSWORD]
            region = user_input.get(CONF_REGION, DEFAULT_REGION)

            await self.async_set_unique_id(_entry_unique_id(email, region))
            self._abort_if_unique_id_configured()

            try:
                client = await self._async_get_logged_in_client(email, password, region)
            except InvertechsAuthError:
                errors["base"] = "invalid_auth"
            except (InvertechsConnectionError, InvertechsError):
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=client.user_data.get("nickName", email),
                    data={
                        CONF_EMAIL: email,
                        CONF_PASSWORD: password,
                        CONF_REGION: region,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self._user_schema(),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reauthentication."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Confirm reauthentication with a new password."""
        reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        errors: dict[str, str] = {}

        if user_input is not None:
            region = _config_entry_region(reauth_entry)
            try:
                await self._async_get_logged_in_client(
                    reauth_entry.data[CONF_EMAIL],
                    user_input[CONF_PASSWORD],
                    region,
                )
            except (InvertechsConnectionError, InvertechsError):
                errors["base"] = "cannot_connect"
            except InvertechsAuthError:
                errors["base"] = "invalid_auth"
            else:
                self.hass.config_entries.async_update_entry(
                    reauth_entry,
                    data={
                        **reauth_entry.data,
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                    },
                )
                await self.hass.config_entries.async_reload(reauth_entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            errors=errors,
        )

    def _user_schema(self) -> vol.Schema:
        return vol.Schema(
            {
                vol.Required(CONF_EMAIL): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Required(CONF_REGION, default=DEFAULT_REGION): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value=REGION_EU, label="Europe"),
                            selector.SelectOptionDict(value=REGION_CN, label="China"),
                        ],
                        translation_key=CONF_REGION,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    ),
                ),
            }
        )

    async def _async_get_logged_in_client(
        self, email: str, password: str, region: str
    ) -> InvertechsClient:
        session = aiohttp_client.async_get_clientsession(self.hass)
        client = InvertechsClient(email, password, session, region=region)
        if not await client.login():
            raise InvertechsAuthError("Invalid credentials")
        return client


class InvertechsOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Invertechs options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            email = self._config_entry.data[CONF_EMAIL]
            region = user_input[CONF_REGION]
            self.hass.config_entries.async_update_entry(
                self._config_entry,
                data={**self._config_entry.data, CONF_REGION: region},
                unique_id=_entry_unique_id(email, region),
            )
            return self.async_create_entry(title="", data=user_input)

        region = _config_entry_region(self._config_entry)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_REGION, default=region): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                selector.SelectOptionDict(
                                    value=REGION_EU,
                                    label="Europe",
                                ),
                                selector.SelectOptionDict(
                                    value=REGION_CN,
                                    label="China",
                                ),
                            ],
                            translation_key=CONF_REGION,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        ),
                    ),
                }
            ),
        )


def _config_entry_region(entry: config_entries.ConfigEntry) -> str:
    return entry.options.get(CONF_REGION, entry.data.get(CONF_REGION, DEFAULT_REGION))
