# Beeminder Dashboard Examples

## Prerequisites
Make sure you have these custom cards installed via HACS:
- mushroom-cards
- auto-entities (for dynamic filtering)
- browser_mod (optional, for popups)

## Quick Setup

### 1. Simple Alert Chip
Shows red when you have goals due today:

```yaml
type: custom:mushroom-chips-card
chips:
  - type: template
    icon: mdi:target-variant
    icon_color: |
      {% set goals = states.sensor 
        | selectattr('entity_id', 'match', 'sensor.beeminder_.*_days_until_derailment')
        | selectattr('state', 'defined')
        | map(attribute='state')
        | map('float', default=999)
        | select('lt', 1)
        | list %}
      {% if goals | length > 0 %}
        red
      {% else %}
        green
      {% endif %}
    content: |
      {% set goals = states.sensor 
        | selectattr('entity_id', 'match', 'sensor.beeminder_.*_days_until_derailment')
        | selectattr('state', 'defined')
        | map(attribute='state')
        | map('float', default=999)
        | select('lt', 1)
        | list %}
      {{ goals | length }} due today
```

### 2. Individual Goal Chips (Auto-Generated)
Creates a chip for each goal that's due soon:

```yaml
type: custom:auto-entities
card:
  type: custom:mushroom-chips-card
filter:
  include:
    - entity_id: sensor.beeminder_*_days_until_derailment
      state: < 1
      options:
        type: template
        icon: mdi:alert-circle
        icon_color: red
        content: >
          {{ state_attr(entity, 'title') | regex_replace(find=' ', replace='') | truncate(10, True, '...', 0) }}
        tap_action:
          action: more-info
```

### 3. Urgency Overview Chips
Three chips showing today/tomorrow/week counts:

```yaml
type: custom:mushroom-chips-card
chips:
  - type: template
    icon: mdi:alert-decagram
    icon_color: red
    content: |
      {% set goals = states.sensor 
        | selectattr('entity_id', 'match', 'sensor.beeminder_.*_days_until_derailment')
        | selectattr('state', 'defined')
        | rejectattr('state', 'in', ['unknown', 'unavailable'])
        | selectattr('state', 'lt', '1')
        | list %}
      Today: {{ goals | length }}
  
  - type: template
    icon: mdi:alert
    icon_color: orange
    content: |
      {% set goals = states.sensor 
        | selectattr('entity_id', 'match', 'sensor.beeminder_.*_days_until_derailment')
        | selectattr('state', 'defined')
        | rejectattr('state', 'in', ['unknown', 'unavailable'])
        | selectattr('state', 'ge', '1')
        | selectattr('state', 'lt', '2')
        | list %}
      Tomorrow: {{ goals | length }}

  - type: template
    icon: mdi:calendar-week
    icon_color: yellow
    content: |
      {% set goals = states.sensor 
        | selectattr('entity_id', 'match', 'sensor.beeminder_.*_days_until_derailment')
        | selectattr('state', 'defined')
        | rejectattr('state', 'in', ['unknown', 'unavailable'])
        | selectattr('state', 'lt', '7')
        | list %}
      Week: {{ goals | length }}
```

### 4. Minimalist Status Chip
Single chip with emoji status:

```yaml
type: custom:mushroom-chips-card
chips:
  - type: template
    icon: mdi:bee
    icon_color: >
      {% set min_days = states.sensor 
        | selectattr('entity_id', 'match', 'sensor.beeminder_.*_days_until_derailment')
        | selectattr('state', 'defined')
        | rejectattr('state', 'in', ['unknown', 'unavailable'])
        | map(attribute='state')
        | map('float', default=999)
        | min %}
      {% if min_days < 1 %}
        red
      {% elif min_days < 2 %}
        orange
      {% elif min_days < 4 %}
        yellow
      {% else %}
        green
      {% endif %}
    content: >
      {% set urgent = states.sensor 
        | selectattr('entity_id', 'match', 'sensor.beeminder_.*_days_until_derailment')
        | selectattr('state', 'defined')
        | rejectattr('state', 'in', ['unknown', 'unavailable'])
        | selectattr('state', 'lt', '1')
        | list | length %}
      {% set soon = states.sensor 
        | selectattr('entity_id', 'match', 'sensor.beeminder_.*_days_until_derailment')
        | selectattr('state', 'defined')
        | rejectattr('state', 'in', ['unknown', 'unavailable'])
        | selectattr('state', 'ge', '1')
        | selectattr('state', 'lt', '3')
        | list | length %}
      {% if urgent > 0 %}
        🚨 {{ urgent }}
      {% elif soon > 0 %}
        ⚠️ {{ soon }}
      {% else %}
        ✅ All good
      {% endif %}
```

## Full Dashboard Example

Here's a complete Beeminder section for your dashboard:

```yaml
type: vertical-stack
cards:
  # Header with chips
  - type: custom:mushroom-chips-card
    chips:
      - type: template
        icon: mdi:bee
        icon_color: amber
        content: Beeminder
      - type: template
        icon: mdi:alert-circle
        icon_color: >
          {% set urgent = states.sensor 
            | selectattr('entity_id', 'match', 'sensor.beeminder_.*_days_until_derailment')
            | selectattr('state', 'lt', '1')
            | list | length %}
          {% if urgent > 0 %}red{% else %}green{% endif %}
        content: >
          {% set urgent = states.sensor 
            | selectattr('entity_id', 'match', 'sensor.beeminder_.*_days_until_derailment')
            | selectattr('state', 'lt', '1')
            | list | length %}
          {{ urgent }} due today

  # Goals needing attention
  - type: conditional
    conditions:
      - condition: template
        value_template: >
          {% set urgent = states.sensor 
            | selectattr('entity_id', 'match', 'sensor.beeminder_.*_days_until_derailment')
            | selectattr('state', 'lt', '3')
            | list | length %}
          {{ urgent > 0 }}
    card:
      type: custom:auto-entities
      card:
        type: entities
        title: Urgent Goals
      filter:
        include:
          - entity_id: sensor.beeminder_*_days_until_derailment
            state: < 3
        options:
          type: custom:mushroom-template-card
          primary: "{{ state_attr(entity, 'title') }}"
          secondary: >
            {% if states(entity) | float < 1 %}
              Due in {{ state_attr(entity, 'hours_until_derailment') | round(1) }} hours!
            {% else %}
              Due in {{ states(entity) | round(0) }} days
            {% endif %}
          icon: mdi:target
          icon_color: >
            {% if states(entity) | float < 1 %}
              red
            {% elif states(entity) | float < 2 %}
              orange
            {% else %}
              yellow
            {% endif %}
          badge_icon: >
            {% if state_attr(entity, 'pledge') > 0 %}
              mdi:currency-usd
            {% endif %}
          badge_color: red
          tap_action:
            action: url
            url_path: "https://www.beeminder.com/{{ state_attr(entity, 'slug') }}"
      sort:
        method: state
        numeric: true
```

## Tips

1. **Placement**: Put chips in your header or at the top of your main dashboard for visibility
2. **Colors**: Red = due today, Orange = due tomorrow, Yellow = due this week
3. **Tap Actions**: Configure to open Beeminder website or show more details
4. **Filtering**: Adjust the state filters to match your preference (e.g., `< 2` for 2 days)
5. **Auto-entities**: Great for dynamic lists that update automatically as deadlines approach