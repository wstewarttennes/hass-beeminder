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

    hass.data[DOMAIN] = {"coordinator": coordinator}

    hass.async_create_task(async_load_platform(hass, "sensor", DOMAIN, {}, config))

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
                        params={
                            **params,
                            "count": 100,
                            "sort": "daystamp",
                        },  # Get last 100 datapoints
                    )
                )
                datapoints_response.raise_for_status()
                datapoints = datapoints_response.json()

                # Store goal data with full datapoints history and all available fields
                goals[slug] = {
                    # Core values
                    "current_value": goal.get("curval", 0),
                    "goal_value": goal.get("goalval", goal.get("rate", 0)),
                    "rate": goal.get("rate", 0),
                    "pledge": goal.get("pledge", 0),
                    "safe_days": goal.get("safebuf", 0),
                    "losedate": goal.get("losedate", ""),
                    "delta": goal.get("delta", 0),
                    
                    # Goal metadata
                    "title": goal.get("title", ""),
                    "goal_type": goal.get("goal_type", ""),
                    "yaxis": goal.get("yaxis", ""),
                    "runits": goal.get("runits", ""),
                    "gunits": goal.get("gunits", ""),
                    "fineprint": goal.get("fineprint", ""),
                    "updated_at": goal.get("updated_at", 0),
                    
                    # Status fields
                    "won": goal.get("won", False),
                    "lost": goal.get("lost", False),
                    "frozen": goal.get("frozen", False),
                    "queued": goal.get("queued", False),
                    "secret": goal.get("secret", False),
                    "datapublic": goal.get("datapublic", True),
                    
                    # Progress tracking
                    "curday": goal.get("curday", 0),
                    "currate": goal.get("currate", 0),
                    "lastday": goal.get("lastday", 0),
                    "initday": goal.get("initday", 0),
                    "initval": goal.get("initval", 0),
                    "goaldate": goal.get("goaldate", 0),
                    
                    # Safety buffer and derailment
                    "safebump": goal.get("safebump", 0),
                    "delta_text": goal.get("delta_text", ""),
                    "limsum": goal.get("limsum", ""),
                    "limsumdays": goal.get("limsumdays", ""),
                    "baremin": goal.get("baremin", ""),
                    "baremintotal": goal.get("baremintotal", ""),
                    
                    # Urgency and scheduling
                    "urgencykey": goal.get("urgencykey", 0),
                    "deadline": goal.get("deadline", 0),
                    "leadtime": goal.get("leadtime", 0),
                    "alertstart": goal.get("alertstart", 0),
                    
                    # Graph and visualization
                    "svg_url": goal.get("svg_url", ""),
                    "graph_url": goal.get("graph_url", ""),
                    "thumb_url": goal.get("thumb_url", ""),
                    "lanewidth": goal.get("lanewidth", 0),
                    "yaw": goal.get("yaw", 0),
                    "dir": goal.get("dir", 0),
                    "lane": goal.get("lane", 0),
                    
                    # Automation and data
                    "autodata": goal.get("autodata", ""),
                    "autoratchet": goal.get("autoratchet", 0),
                    "last_datapoint": goal.get("last_datapoint", {}),
                    "todayta": goal.get("todayta", False),
                    "hhmmformat": goal.get("hhmmformat", False),
                    "integery": goal.get("integery", False),
                    
                    # Advanced settings
                    "aggday": goal.get("aggday", ""),
                    "kyoom": goal.get("kyoom", False),
                    "odom": goal.get("odom", False),
                    "mathishard": goal.get("mathishard", []),
                    "headsum": goal.get("headsum", ""),
                    "steppy": goal.get("steppy", False),
                    "rosy": goal.get("rosy", False),
                    "movingav": goal.get("movingav", False),
                    "aura": goal.get("aura", False),
                    
                    # Contract and road
                    "contract": goal.get("contract", {}),
                    "road": goal.get("road", []),
                    "roadall": goal.get("roadall", []),
                    "fullroad": goal.get("fullroad", []),
                    "rah": goal.get("rah", 0),
                    
                    # Other metadata
                    "id": goal.get("id", ""),
                    "callback_url": goal.get("callback_url", ""),
                    "description": goal.get("description", ""),
                    "graphsum": goal.get("graphsum", ""),
                    "plotall": goal.get("plotall", True),
                    "maxflux": goal.get("maxflux", 0),
                    "maxday": goal.get("maxday", 0),
                    "numpts": goal.get("numpts", 0),
                    
                    # Tags
                    "tags": goal.get("tags", []),
                    
                    # Datapoints
                    "datapoints": [
                        {
                            "timestamp": int(dp.get("timestamp", 0)) * 1000,
                            "value": float(dp.get("value", 0)),
                            "comment": dp.get("comment", ""),
                            "id": dp.get("id", ""),
                        }
                        for dp in datapoints
                    ],
                }
            return goals

        except requests.exceptions.RequestException as err:
            raise UpdateFailed(f"Error communicating with Beeminder API: {err}")
