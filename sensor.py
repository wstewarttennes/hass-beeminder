"""Support for Beeminder sensors."""

from datetime import datetime
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
        entities.append(BeeminderDaysUntilDerailmentSensor(coordinator, goal_slug))

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
                # Return all available goal data as attributes
                return goal_data.copy()
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


class BeeminderDaysUntilDerailmentSensor(BeeminderSensor):
    """Sensor for days until derailment of a Beeminder goal."""

    def __init__(self, coordinator, goal_slug):
        super().__init__(coordinator, goal_slug, "days_until_derailment", "Days Until Derailment", unit="days")
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        """Return the days until derailment."""
        try:
            if self.coordinator.data:
                goal_data = self.coordinator.data.get(self._goal_slug, {})
                losedate = goal_data.get("losedate")
                
                if losedate:
                    # Calculate days until derailment
                    derailment_date = datetime.fromtimestamp(losedate)
                    current_date = datetime.now()
                    days_remaining = (derailment_date - current_date).days
                    
                    # Return days remaining, but not negative
                    return max(0, days_remaining)
                    
                return None
        except Exception:
            return None

    @property
    def extra_state_attributes(self):
        """Return additional attributes specific to derailment."""
        base_attrs = super().extra_state_attributes
        
        try:
            if self.coordinator.data:
                goal_data = self.coordinator.data.get(self._goal_slug, {})
                losedate = goal_data.get("losedate")
                
                if losedate:
                    derailment_date = datetime.fromtimestamp(losedate)
                    current_date = datetime.now()
                    hours_remaining = (derailment_date - current_date).total_seconds() / 3600
                    
                    base_attrs.update({
                        "derailment_date": derailment_date.isoformat(),
                        "hours_until_derailment": max(0, round(hours_remaining, 1)),
                        "is_derailing_soon": hours_remaining <= 24,
                        "is_derailing_today": hours_remaining <= 0,
                    })
                    
        except Exception:
            pass
            
        return base_attrs
