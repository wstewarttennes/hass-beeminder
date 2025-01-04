"""Support for Beeminder sensors."""
import logging
from typing import Any, Dict, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.typing import HomeAssistantType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(
    hass: HomeAssistantType,
    config: Dict[str, Any],
    async_add_entities,
    discovery_info=None,
) -> None:
    """Set up the Beeminder sensor platform."""
    coordinator = hass.data[DOMAIN]["coordinator"]

    entities = []
    for goal_slug in coordinator.data:
        entities.append(BeeminderSensor(coordinator, goal_slug))

    async_add_entities(entities, True)

class BeeminderSensor(CoordinatorEntity, SensorEntity):
    """Implementation of a Beeminder sensor."""

    def __init__(self, coordinator, goal_slug):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._goal_slug = goal_slug
        self._attr_unique_id = f"beeminder_{goal_slug}"
        self._attr_name = f"Beeminder {goal_slug}"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self.coordinator.data[self._goal_slug]["current_value"]

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            "rate": self.coordinator.data[self._goal_slug]["rate"],
            "goal_value": self.coordinator.data[self._goal_slug]["goal_value"],
            "pledge": self.coordinator.data[self._goal_slug]["pledge"],
            "safe_days": self.coordinator.data[self._goal_slug]["safe_days"],
            "losedate": self.coordinator.data[self._goal_slug]["losedate"],
            "delta": self.coordinator.data[self._goal_slug]["delta"]
        }
