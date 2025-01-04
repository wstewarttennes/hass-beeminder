from homeassistant import config_entries
from homeassistant.core import HomeAssistant
import voluptuous as vol
from .const import DOMAIN, CONF_USERNAME, CONF_AUTH_TOKEN

class BeeminderConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    
    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            # Validate the credentials here
            return self.async_create_entry(
                title=user_input[CONF_USERNAME],
                data=user_input
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_AUTH_TOKEN): str,
            }),
            errors=errors,
        )
