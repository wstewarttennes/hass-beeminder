# Beeminder Home Assistant Integration

A comprehensive Home Assistant integration for [Beeminder](https://www.beeminder.com) that enables goal tracking, voice control, and automation.

## Features

- 📊 **Real-time Goal Tracking**: Monitor all your Beeminder goals as Home Assistant sensors
- 🎯 **Derailment Alerts**: Track days/hours until goal derailment with automatic warnings
- 🎙️ **Voice Control**: Add datapoints using natural language through your voice assistant
- 🔔 **Smart Notifications**: Automated announcements for goals due today
- 📈 **Rich Data**: Access complete goal statistics, history, and metadata
- 🏠 **Full Integration**: Create automations based on goal status

## What's Included

### Sensors (per goal)
1. **Current Value** - Track your goal's current cumulative value
2. **Goal Target** - Monitor the dynamic target value
3. **Days Until Derailment** - See how many days you have left

### Attributes Available
Each sensor exposes 60+ attributes including:
- Complete datapoint history (last 100 entries)
- Goal metadata (title, type, pledge amount, etc.)
- Progress tracking (rate, safebuffer, urgency)
- Status flags (won, lost, frozen)
- Graph URLs for visualization

## Installation

### 1. Install the Integration

Copy the `beeminder` folder to your `custom_components` directory:
```
custom_components/
└── beeminder/
    ├── __init__.py
    ├── sensor.py
    ├── config_flow.py
    ├── const.py
    └── manifest.json
```

### 2. Configure via YAML

Add to your `configuration.yaml`:
```yaml
beeminder:
  username: !secret beeminder_username
  auth_token: !secret beeminder_token
```

Add to your `secrets.yaml`:
```yaml
beeminder_username: YOUR_USERNAME
beeminder_token: YOUR_AUTH_TOKEN
```

Get your auth token from: https://www.beeminder.com/api/v1/auth_token.json

### 3. Restart Home Assistant

## Voice Assistant Setup

### Prerequisites
1. Install [Extended OpenAI Conversation](https://github.com/jekalmin/extended_openai_conversation) via HACS
2. Configure it with your preferred AI provider (OpenAI, OpenRouter for Claude, etc.)

### Quick Setup

For complete configuration details, see [VOICE_ASSISTANT_SETUP.md](VOICE_ASSISTANT_SETUP.md).

### 1. Create Template Sensors

Create file `packages/beeminder_templates.yaml` with sensors for different time periods:
```yaml
template:
  sensor:
    - name: "Beeminder Goals Derailing Today"
      state: >
        {% set goals = states.sensor | selectattr('entity_id', 'match', 'sensor.beeminder_.*_days_until_derailment') | selectattr('state', 'eq', '0') | list %}
        {% if goals | length > 0 %}
          {{ goals | map(attribute='attributes.title') | list | join(', ') }}
        {% else %}
          No goals derailing today
        {% endif %}
```

### 2. Add Voice Control Script

Add to `scripts.yaml`:
```yaml
add_beeminder_datapoint:
  alias: Add Beeminder Datapoint
  description: 'Add a datapoint to a Beeminder goal via voice'
  mode: single
  fields:
    value:
      description: The numeric value to add
      required: true
    goal:
      description: The Beeminder goal name
      required: true
    date:
      description: Date for the datapoint (YYYY-MM-DD)
      required: false
    comment:
      description: Optional comment
      required: false
  sequence:
    - variables:
        username: !secret beeminder_username
        auth_token: !secret beeminder_token
        goal_slug: >
          {% set g = goal | lower | replace(' ', '-') | replace('beeminder', '') | trim %}
          {% if g in ['push-ups', 'push ups', 'pushup'] %}
            pushups
          {% elif g in ['code', 'programming'] %}
            coding
          {% else %}
            {{ g }}
          {% endif %}
        daystamp: >
          {% if date is defined and date %}
            {{ date }}
          {% else %}
            {{ now().strftime('%Y-%m-%d') }}
          {% endif %}
        comment_text: "{{ comment | default('Added via Home Assistant') }}"
    - service: rest_command.beeminder_add_datapoint
      data:
        goal: "{{ goal_slug }}"
        value: "{{ value }}"
        daystamp: "{{ daystamp }}"
        comment: "{{ comment_text }}"
        auth_token: "{{ auth_token }}"
```

### 3. Configure Extended OpenAI Functions

Add these functions to Extended OpenAI Conversation:

**Add Data Function:**
```yaml
- spec:
    name: add_beeminder_data
    description: Immediately add data to a Beeminder goal without asking for confirmation
    parameters:
      type: object
      properties:
        goal:
          type: string
          description: The Beeminder goal name
        value:
          type: number
          description: The numeric value to add
      required:
      - goal
      - value
  function:
    type: script
    sequence:
    - service: script.add_beeminder_datapoint
      data:
        goal: "{{ goal }}"
        value: "{{ value }}"
        comment: "Added via voice AI"
```

**Check Status Function:**
```yaml
- spec:
    name: get_beeminder_status
    description: Get information about Beeminder goals status
    parameters:
      type: object
      properties:
        time_period:
          type: string
          description: Time period to check
          enum: [today, tomorrow, soon, week, safe, most_urgent, count, all]
          default: today
  function:
    type: template
    value_template: >
      {% if time_period == 'today' %}
        {{ states('sensor.beeminder_goals_derailing_today') }}
      {% elif time_period == 'tomorrow' %}
        {{ states('sensor.beeminder_goals_derailing_tomorrow') }}
      {% elif time_period == 'week' %}
        {{ states('sensor.beeminder_goals_derailing_this_week') }}
      {% else %}
        {{ states('sensor.beeminder_goals_derailing_today') }}
      {% endif %}
```

### Voice Commands

**Adding Data:**
- "Add 10 pushups to Beeminder"
- "Log 30 minutes of coding"
- "Record 5000 steps"
- "I did 2 floss"

**Checking Status:**
- "What Beeminder goals am I derailing on today?"
- "What goals are due tomorrow?"
- "What goals are derailing this week?"
- "What's my most urgent Beeminder goal?"

## Automation Examples

### Daily Derailment Alert
```yaml
automation:
  - alias: "Beeminder 6PM Derailment Alert"
    trigger:
      - platform: time
        at: "18:00:00"
    action:
      - variables:
          urgent_goals: >
            {% set goals = states.sensor 
              | selectattr('entity_id', 'match', 'sensor.beeminder_.*_days_until_derailment')
              | selectattr('state', 'lt', '1')
              | list %}
            {% if goals | length > 0 %}
              {{ goals | map(attribute='attributes.title') | list | join(', ') }}
            {% else %}
              none
            {% endif %}
      - condition: template
        value_template: "{{ urgent_goals != 'none' }}"
      - service: tts.speak
        data:
          message: "Attention! These Beeminder goals are due today: {{ urgent_goals }}"
```

### Auto-log Daily Habits
```yaml
automation:
  - alias: "Log Toothbrushing"
    trigger:
      - platform: state
        entity_id: binary_sensor.bathroom_motion
        to: "on"
        for: "00:02:00"
    condition:
      - condition: time
        after: "21:00:00"
        before: "23:59:00"
    action:
      - service: script.add_beeminder_datapoint
        data:
          goal: "toothbrush"
          value: 1
          comment: "Auto-logged by motion sensor"
```

## Template Sensors

The integration includes comprehensive template sensors for tracking goal urgency across different time periods. These are especially useful for voice assistant queries and dashboard cards.

### Available Template Sensors

Create these in `packages/beeminder_templates.yaml`:

1. **Goals Derailing Today** - Lists all goals with 0 days until derailment
2. **Goals Derailing Tomorrow** - Lists all goals with 1 day until derailment  
3. **Goals Derailing Soon** - Lists goals derailing in 2-3 days
4. **Goals Derailing This Week** - Lists all goals derailing within 7 days
5. **Safe Goals** - Lists goals with more than 7 days buffer
6. **Most Urgent Goal** - Shows your single most urgent goal
7. **Goals Count by Urgency** - Shows counts for today, tomorrow, and this week

### Example Template Sensor Configuration

```yaml
template:
  sensor:
    - name: "Beeminder Goals Derailing This Week"
      state: >
        {% set goals = states.sensor 
          | selectattr('entity_id', 'match', 'sensor.beeminder_.*_days_until_derailment') 
          | selectattr('state', 'le', '7') 
          | list %}
        {% if goals | length > 0 %}
          {% set ns = namespace(names=[]) %}
          {% for goal in goals %}
            {% set title = goal.attributes.get('title', '') %}
            {% set goal_name = title if title else goal.entity_id.replace('sensor.beeminder_', '').replace('_days_until_derailment', '').replace('_', ' ').title() %}
            {% set ns.names = ns.names + [goal_name + ': ' + goal.state + ' days'] %}
          {% endfor %}
          {{ ns.names | join(', ') }}
        {% else %}
          No goals derailing this week
        {% endif %}
```

### Using Template Sensors in Automations

```yaml
automation:
  - alias: "Morning Goal Report"
    trigger:
      - platform: time
        at: "08:00:00"
    condition:
      - condition: template
        value_template: "{{ states('sensor.beeminder_goals_derailing_today') != 'No goals derailing today' }}"
    action:
      - service: notify.mobile_app
        data:
          title: "Beeminder Goals Due Today"
          message: "{{ states('sensor.beeminder_goals_derailing_today') }}"
```

## Dashboard Cards

### Mushroom Card - Status Chip
```yaml
type: custom:mushroom-template-card
icon: mdi:bee
icon_color: >-
  {% set min_days = states.sensor 
    | selectattr('entity_id', 'match', 'sensor.beeminder_.*_days_until_derailment')
    | map(attribute='state')
    | map('float', default=999)
    | min %}
  {% if min_days < 1 %} red
  {% elif min_days < 2 %} orange
  {% elif min_days < 4 %} yellow
  {% else %} green
  {% endif %}
primary: Beeminder
secondary: >-
  {% set urgent = states.sensor 
    | selectattr('entity_id', 'match', 'sensor.beeminder_.*_days_until_derailment')
    | selectattr('state', 'lt', '1')
    | list | length %}
  {% if urgent > 0 %} 🚨 {{ urgent }} due today
  {% else %} ✅ All good
  {% endif %}
```

### Goals Due Today
```yaml
type: custom:auto-entities
card:
  type: entities
  title: ⚠️ Beeminder Goals Due Today
filter:
  include:
    - entity_id: sensor.beeminder_*_days_until_derailment
      state: < 1
```

## Troubleshooting

### Goals Not Updating
- Check your auth token is valid
- Ensure your username is correct
- Default update interval is 5 minutes

### Voice Commands Not Working
- Verify Extended OpenAI Conversation is installed
- Check the function is properly configured
- Ensure your voice pipeline uses the Extended OpenAI agent

### REST Command Errors
- Check Home Assistant logs for API errors
- Verify goal slugs match exactly (case-sensitive)
- Test manually via Developer Tools → Services

## Advanced Usage

### Access All Goal Data
Every sensor includes complete goal data as attributes:
```yaml
{{ state_attr('sensor.beeminder_pushups_current_value', 'pledge') }}
{{ state_attr('sensor.beeminder_weight_days_until_derailment', 'hours_until_derailment') }}
{{ state_attr('sensor.beeminder_coding_current_value', 'datapoints') | length }}
```

### Template Examples
```yaml
# Check if any goal is urgent
{{ states.sensor 
  | selectattr('entity_id', 'match', 'sensor.beeminder_.*_days_until_derailment')
  | selectattr('state', 'lt', '1')
  | list | length > 0 }}

# Get total pledged amount
{{ states.sensor 
  | selectattr('entity_id', 'match', 'sensor.beeminder_.*_current_value')
  | map(attribute='attributes.pledge')
  | sum }}
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.

## Acknowledgments

- [Beeminder](https://www.beeminder.com) for the API and goal tracking platform
- Home Assistant community for the amazing automation platform
- Extended OpenAI Conversation for enabling natural voice control