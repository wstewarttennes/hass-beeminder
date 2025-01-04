"""Support for Beeminder sensors."""

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_platform(
    hass: HomeAssistant,
    config,
    async_add_entities,
    discovery_info=None,
) -> None:
    """Set up the Beeminder sensor platform."""
    coordinator = hass.data[DOMAIN]["coordinator"]

    entities = []
    for goal_slug in coordinator.data:
        entities.append(BeeminderCurrentValueSensor(coordinator, goal_slug))
        entities.append(BeeminderGoalValueSensor(coordinator, goal_slug))

    async_add_entities(entities, True)


class BeeminderSensor(CoordinatorEntity, SensorEntity):
    """Base class for Beeminder sensors."""

    def __init__(self, coordinator, goal_slug, value_key, name_suffix, unit="total"):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._goal_slug = goal_slug
        self._value_key = value_key
        self._attr_unique_id = f"beeminder_{goal_slug}_{value_key}"
        self._attr_name = f"Beeminder {goal_slug} {name_suffix}"
        self._attr_native_unit_of_measurement = unit
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        """Return the sensor value."""
        try:
            if self.coordinator.data:
                goal_data = self.coordinator.data.get(self._goal_slug, {})
                return float(goal_data.get(self._value_key, 0))
            return None
        except Exception:
            return None

    @property
    def extra_state_attributes(self):
        """Return additional attributes."""
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
                    "datapoints": goal_data.get("datapoints", []),
                }
            return {}
        except Exception:
            return {}


class BeeminderCurrentValueSensor(BeeminderSensor):
    """Sensor for the current value of a Beeminder goal."""

    def __init__(self, coordinator, goal_slug):
        super().__init__(coordinator, goal_slug, "current_value", "Current Value")


class BeeminderGoalValueSensor(BeeminderSensor):
    """Sensor for the dynamic goal value of a Beeminder goal."""

    def __init__(self, coordinator, goal_slug):
        super().__init__(coordinator, goal_slug, "goal_value", "Goal")

    @property
    def native_value(self):
        """Return the goal value of the sensor."""
        try:
            if self.coordinator.data:
                goal_data = self.coordinator.data.get(self._goal_slug, {})
                return float(goal_data.get("goal_value") or goal_data.get("rate") or 0)
            return None
        except Exception:
            return None
