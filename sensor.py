"""Support for Beeminder sensors."""
from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.helpers.typing import HomeAssistantType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

async def async_setup_platform(
    hass: HomeAssistantType,
    config,
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
        self._attr_native_unit_of_measurement = "total"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        """Return the state of the sensor."""
        try:
            if self.coordinator.data:
                goal_data = self.coordinator.data.get(self._goal_slug, {})
                datapoints = goal_data.get("datapoints", [])
                if datapoints:
                    return float(datapoints[0].get("value", 0))
            return None
        except Exception as e:
            return None

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        try:
            if self.coordinator.data:
                goal_data = self.coordinator.data.get(self._goal_slug, {})
                return {
                    "rate": goal_data.get("rate", 0),
                    "goal_value": goal_data.get("goal_value", 0),
                    "pledge": goal_data.get("pledge", 0),
                    "safe_days": goal_data.get("safe_days", 0),
                    "losedate": goal_data.get("losedate", ""),
                    "delta": goal_data.get("delta", 0),
                    "datapoints": goal_data.get("datapoints", [])
                }
            return {}
        except Exception:
            return {}
