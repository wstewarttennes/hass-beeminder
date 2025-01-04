"""The Beeminder integration."""
import logging
from datetime import timedelta

import requests
import voluptuous as vol

from homeassistant.const import CONF_USERNAME
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, CONF_AUTH_TOKEN, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_AUTH_TOKEN): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Beeminder component."""
    if DOMAIN not in config:
        return True

    conf = config[DOMAIN]
    username = conf[CONF_USERNAME]
    auth_token = conf[CONF_AUTH_TOKEN]

    coordinator = BeeminderDataUpdateCoordinator(hass, username, auth_token)
    await coordinator.async_refresh()
    
    hass.data[DOMAIN] = {
        "coordinator": coordinator
    }

    hass.async_create_task(
        async_load_platform(hass, "sensor", DOMAIN, {}, config)
    )

    return True

class BeeminderDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Beeminder data."""

    def __init__(self, hass, username, auth_token):
        """Initialize the data updater."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.username = username
        self.auth_token = auth_token
        self.base_url = f"https://www.beeminder.com/api/v1/users/{username}"

    async def _async_update_data(self):
        """Fetch data from Beeminder."""
        try:
            goals = {}
            params = {"auth_token": self.auth_token}
            
            # Fetch goals
            response = await self.hass.async_add_executor_job(
                lambda: requests.get(f"{self.base_url}/goals.json", params=params)
            )
            response.raise_for_status()
            goals_data = response.json()
            
            # Process each goal and fetch its datapoints
            for goal in goals_data:
                slug = goal["slug"]
                
                # Fetch datapoints for this goal
                datapoints_response = await self.hass.async_add_executor_job(
                    lambda: requests.get(
                        f"{self.base_url}/goals/{slug}/datapoints.json",
                        params={**params, "count": 100, "sort": "daystamp"}  # Get last 100 datapoints
                    )
                )
                datapoints_response.raise_for_status()
                datapoints = datapoints_response.json()
                
                # Store goal data with full datapoints history
                goals[slug] = {
                    "current_value": goal.get("curval", 0),
                    "rate": goal.get("rate", 0),
                    "goal_value": goal.get("goalval", 0),
                    "pledge": goal.get("pledge", 0),
                    "safe_days": goal.get("safebuf", 0),
                    "losedate": goal.get("losedate", ""),
                    "delta": goal.get("delta", 0),
                    "datapoints": [
                        {
                            "timestamp": int(dp.get("timestamp", 0)) * 1000,  # Convert to milliseconds for ApexCharts
                            "value": float(dp.get("value", 0))
                        }
                        for dp in datapoints
                    ]
                }
            
            return goals

        except requests.exceptions.RequestException as err:
            raise UpdateFailed(f"Error communicating with Beeminder API: {err}")
