# Beeminder Voice Assistant Setup Guide

This guide provides complete configuration for voice control of Beeminder through Home Assistant.

## Prerequisites

1. Beeminder integration installed and configured
2. [Extended OpenAI Conversation](https://github.com/jekalmin/extended_openai_conversation) installed via HACS
3. API provider configured (OpenAI, OpenRouter, etc.)

## Required Script Configuration

Add this to your `scripts.yaml`:

```yaml
add_beeminder_datapoint:
  alias: Add Beeminder Datapoint
  description: 'Add a datapoint to a Beeminder goal via voice'
  mode: single
  fields:
    value:
      description: The numeric value to add
      required: true
      example: 10
    goal:
      description: The Beeminder goal name
      required: true
      example: pushups
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

## Complete Extended OpenAI Configuration

Add all these functions to your Extended OpenAI Conversation integration:

```yaml
# Function 1: Execute Home Assistant Services (standard)
- spec:
    name: execute_services
    description: Use this function to execute service of devices in Home Assistant.
    parameters:
      type: object
      properties:
        list:
          type: array
          items:
            type: object
            properties:
              domain:
                type: string
                description: The domain of the service
              service:
                type: string
                description: The service to be called
              service_data:
                type: object
                description: The service data object to indicate what to control.
                properties:
                  entity_id:
                    type: string
                    description: The entity_id retrieved from available devices. It must start with domain, followed by dot character.
                required:
                - entity_id
            required:
            - domain
            - service
            - service_data
  function:
    type: native
    name: execute_service

# Function 2: Add Beeminder Datapoints
- spec:
    name: add_beeminder_data
    description: Add data to a Beeminder goal. The script will map common goal names (like triceps->tricepdips, pushups variations, etc.)
    parameters:
      type: object
      properties:
        goal:
          type: string
          description: The Beeminder goal name like pushups, coding, weight, triceps
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
      continue_on_error: false
      response_variable: script_result
    - stop: >
        {% if script_result is defined and script_result.result is defined %}
          {{ script_result.result }}
        {% else %}
          I've sent {{ value }} to your {{ goal }} goal. Please check Beeminder to confirm it was added successfully.
        {% endif %}

# Function 3: Get Beeminder Status (Enhanced)
- spec:
    name: get_beeminder_status
    description: Get information about Beeminder goals status. Use this when user asks about their Beeminder goals - today, tomorrow, this week, or safe goals.
    parameters:
      type: object
      properties:
        time_period:
          type: string
          description: Time period to check for derailing goals
          enum:
            - today
            - tomorrow
            - soon
            - week
            - safe
            - most_urgent
            - count
            - all
          default: today
  function:
    type: template
    value_template: >
      {% if time_period == 'today' %}
        {{ states('sensor.beeminder_goals_derailing_today') }}
      {% elif time_period == 'tomorrow' %}
        {{ states('sensor.beeminder_goals_derailing_tomorrow') }}
      {% elif time_period == 'soon' %}
        {{ states('sensor.beeminder_goals_derailing_soon') }}
      {% elif time_period == 'week' %}
        {{ states('sensor.beeminder_goals_derailing_this_week') }}
      {% elif time_period == 'safe' %}
        {{ states('sensor.beeminder_safe_goals') }}
      {% elif time_period == 'most_urgent' %}
        Your most urgent goal is: {{ states('sensor.beeminder_most_urgent_goal') }}
      {% elif time_period == 'count' %}
        {{ states('sensor.beeminder_goals_count_by_urgency') }}
      {% else %}
        Today: {{ states('sensor.beeminder_goals_derailing_today') }}
        Tomorrow: {{ states('sensor.beeminder_goals_derailing_tomorrow') }}
        This week: {{ states('sensor.beeminder_goals_derailing_this_week') }}
        Most urgent: {{ states('sensor.beeminder_most_urgent_goal') }}
      {% endif %}
```

## Required REST Command

Add this to your `configuration.yaml`:

```yaml
rest_command:
  beeminder_add_datapoint:
    url: "https://www.beeminder.com/api/v1/users/{{ states('input_text.beeminder_username') | default('YOUR_USERNAME') }}/goals/{{ goal }}/datapoints.json"
    method: post
    payload: '{"value": {{ value }}, "daystamp": "{{ daystamp }}", "comment": "{{ comment }}", "auth_token": "{{ auth_token }}"}'
    content_type: 'application/json'
    verify_ssl: true
```

## Template Sensors Configuration

Create a file at `packages/beeminder_templates.yaml`:

```yaml
template:
  sensor:
    - name: "Beeminder Goals Derailing Today"
      state: >
        {% set goals = states.sensor | selectattr('entity_id', 'match', 'sensor.beeminder_.*_days_until_derailment') | selectattr('state', 'defined') | rejectattr('state', 'in', ['unknown', 'unavailable']) | selectattr('state', 'eq', '0') | list %}
        {% if goals | length > 0 %}
          {% set ns = namespace(names=[]) %}
          {% for goal in goals %}
            {% set title = goal.attributes.get('title', '') %}
            {% if title %}
              {% set ns.names = ns.names + [title] %}
            {% else %}
              {% set goal_name = goal.entity_id.replace('sensor.beeminder_', '').replace('_days_until_derailment', '').replace('_', ' ').title() %}
              {% set ns.names = ns.names + [goal_name] %}
            {% endif %}
          {% endfor %}
          {{ ns.names | join(', ') }}
        {% else %}
          No goals derailing today
        {% endif %}
        
    - name: "Beeminder Goals Derailing Tomorrow"
      state: >
        {% set goals = states.sensor | selectattr('entity_id', 'match', 'sensor.beeminder_.*_days_until_derailment') | selectattr('state', 'defined') | rejectattr('state', 'in', ['unknown', 'unavailable']) | selectattr('state', 'eq', '1') | list %}
        {% if goals | length > 0 %}
          {% set ns = namespace(names=[]) %}
          {% for goal in goals %}
            {% set title = goal.attributes.get('title', '') %}
            {% if title %}
              {% set ns.names = ns.names + [title] %}
            {% else %}
              {% set goal_name = goal.entity_id.replace('sensor.beeminder_', '').replace('_days_until_derailment', '').replace('_', ' ').title() %}
              {% set ns.names = ns.names + [goal_name] %}
            {% endif %}
          {% endfor %}
          {{ ns.names | join(', ') }}
        {% else %}
          No goals derailing tomorrow
        {% endif %}
        
    - name: "Beeminder Goals Derailing Soon"
      state: >
        {% set goals = states.sensor | selectattr('entity_id', 'match', 'sensor.beeminder_.*_days_until_derailment') | selectattr('state', 'defined') | rejectattr('state', 'in', ['unknown', 'unavailable']) | selectattr('state', 'ge', '2') | selectattr('state', 'le', '3') | list %}
        {% if goals | length > 0 %}
          {% set ns = namespace(names=[]) %}
          {% for goal in goals %}
            {% set title = goal.attributes.get('title', '') %}
            {% if title %}
              {% set ns.names = ns.names + [title + ': ' + goal.state + ' days'] %}
            {% else %}
              {% set goal_name = goal.entity_id.replace('sensor.beeminder_', '').replace('_days_until_derailment', '').replace('_', ' ').title() %}
              {% set ns.names = ns.names + [goal_name + ': ' + goal.state + ' days'] %}
            {% endif %}
          {% endfor %}
          {{ ns.names | join(', ') }}
        {% else %}
          No goals derailing soon
        {% endif %}
        
    - name: "Beeminder Goals Derailing This Week"
      state: >
        {% set goals = states.sensor | selectattr('entity_id', 'match', 'sensor.beeminder_.*_days_until_derailment') | selectattr('state', 'defined') | rejectattr('state', 'in', ['unknown', 'unavailable']) | selectattr('state', 'le', '7') | list %}
        {% if goals | length > 0 %}
          {% set ns = namespace(names=[]) %}
          {% for goal in goals %}
            {% set title = goal.attributes.get('title', '') %}
            {% if title %}
              {% set ns.names = ns.names + [title + ': ' + goal.state + ' days'] %}
            {% else %}
              {% set goal_name = goal.entity_id.replace('sensor.beeminder_', '').replace('_days_until_derailment', '').replace('_', ' ').title() %}
              {% set ns.names = ns.names + [goal_name + ': ' + goal.state + ' days'] %}
            {% endif %}
          {% endfor %}
          {{ ns.names | join(', ') }}
        {% else %}
          No goals derailing this week
        {% endif %}
        
    - name: "Beeminder Goals Count by Urgency"
      state: >
        {% set today = states.sensor | selectattr('entity_id', 'match', 'sensor.beeminder_.*_days_until_derailment') | selectattr('state', 'defined') | rejectattr('state', 'in', ['unknown', 'unavailable']) | selectattr('state', 'eq', '0') | list | length %}
        {% set tomorrow = states.sensor | selectattr('entity_id', 'match', 'sensor.beeminder_.*_days_until_derailment') | selectattr('state', 'defined') | rejectattr('state', 'in', ['unknown', 'unavailable']) | selectattr('state', 'eq', '1') | list | length %}
        {% set week = states.sensor | selectattr('entity_id', 'match', 'sensor.beeminder_.*_days_until_derailment') | selectattr('state', 'defined') | rejectattr('state', 'in', ['unknown', 'unavailable']) | selectattr('state', 'le', '7') | list | length %}
        Today: {{ today }}, Tomorrow: {{ tomorrow }}, This week: {{ week }}
      attributes:
        today_count: >
          {{ states.sensor | selectattr('entity_id', 'match', 'sensor.beeminder_.*_days_until_derailment') | selectattr('state', 'defined') | rejectattr('state', 'in', ['unknown', 'unavailable']) | selectattr('state', 'eq', '0') | list | length }}
        tomorrow_count: >
          {{ states.sensor | selectattr('entity_id', 'match', 'sensor.beeminder_.*_days_until_derailment') | selectattr('state', 'defined') | rejectattr('state', 'in', ['unknown', 'unavailable']) | selectattr('state', 'eq', '1') | list | length }}
        week_count: >
          {{ states.sensor | selectattr('entity_id', 'match', 'sensor.beeminder_.*_days_until_derailment') | selectattr('state', 'defined') | rejectattr('state', 'in', ['unknown', 'unavailable']) | selectattr('state', 'le', '7') | list | length }}
          
    - name: "Beeminder Most Urgent Goal"
      state: >
        {% set goals = states.sensor | selectattr('entity_id', 'match', 'sensor.beeminder_.*_days_until_derailment') | selectattr('state', 'defined') | rejectattr('state', 'in', ['unknown', 'unavailable']) | list %}
        {% if goals | length > 0 %}
          {% set most_urgent = goals | min(attribute='state') %}
          {% set title = most_urgent.attributes.get('title', '') %}
          {% if title %}
            {{ title }}: {{ most_urgent.state }} days
          {% else %}
            {% set goal_name = most_urgent.entity_id.replace('sensor.beeminder_', '').replace('_days_until_derailment', '').replace('_', ' ').title() %}
            {{ goal_name }}: {{ most_urgent.state }} days
          {% endif %}
        {% else %}
          No active goals
        {% endif %}
        
    - name: "Beeminder Safe Goals"
      state: >
        {% set goals = states.sensor | selectattr('entity_id', 'match', 'sensor.beeminder_.*_days_until_derailment') | selectattr('state', 'defined') | rejectattr('state', 'in', ['unknown', 'unavailable']) | selectattr('state', 'gt', '7') | list %}
        {% if goals | length > 0 %}
          {% set ns = namespace(names=[]) %}
          {% for goal in goals %}
            {% set title = goal.attributes.get('title', '') %}
            {% if title %}
              {% set ns.names = ns.names + [title + ': ' + goal.state + ' days'] %}
            {% else %}
              {% set goal_name = goal.entity_id.replace('sensor.beeminder_', '').replace('_days_until_derailment', '').replace('_', ' ').title() %}
              {% set ns.names = ns.names + [goal_name + ': ' + goal.state + ' days'] %}
            {% endif %}
          {% endfor %}
          {{ ns.names | join(', ') }}
        {% else %}
          No safe goals
        {% endif %}
```

## Voice Commands Examples

### Adding Data
All goals support multiple variations:
- **Pushups**: "Add 10 pushups", "I did 10 push-ups", "10 push ups"
- **Pullups**: "Add 5 pullups", "I did 5 pull-ups", "5 pull ups"
- **Coding**: "30 minutes of coding", "I coded for 30 minutes", "programming 30"
- **Triceps**: "15 triceps", "I did 15 tricep dips", "15 triceps-dips"
- **Stretch**: "I stretched", "1 stretching", "did my stretches"
- **Floss**: "I flossed", "dental floss 1", "flossing done"
- **Toothbrush**: "brushed my teeth", "tooth brush 1", "brushing done"
- **Ice cream**: "ate ice cream", "had dessert", "ice-cream 1"
- **Crunches**: "did 20 crunches", "20 abs", "20 sit-ups"
- **Sing**: "practiced singing", "vocal practice", "voice 1"
- **Random exercise**: "random exercise done", "did exercise"
- **Meds**: "took medication", "medicine taken", "pills 1"
- **Steps**: "5000 steps", "walked 5000", "step count 5000"

### Checking Status
- "What Beeminder goals am I derailing on today?"
- "What goals are due tomorrow?"
- "What goals are derailing this week?"
- "What's my most urgent Beeminder goal?"
- "What are my safe goals?"
- "How many Beeminder goals am I tracking?"

### Extended OpenAI Prompt Configuration

Add this to your Extended OpenAI system prompt for better handling:

```
When the user asks about Beeminder goals:
- For "what goals am I derailing on?" default to today
- For "what goals are due?" check today
- Always confirm when adding datapoints with the exact value and goal name
- If goal names are ambiguous, ask for clarification
```

## Troubleshooting

### Voice Commands Not Working
1. Check that all template sensors exist in Developer Tools → States
2. Verify the Extended OpenAI functions are configured correctly
3. Test the script manually: Developer Tools → Services → script.add_beeminder_datapoint

### Goals Not Found
- Ensure template sensors are created and showing data
- Check sensor names match exactly (case-sensitive)
- Verify goals are updating (check last_updated in Developer Tools)

### Common Issues
- "No goals derailing today" when you have goals due: Check that sensors show 0 days, not "unknown"
- Voice assistant not understanding: Try being more specific, e.g., "What Beeminder goals am I derailing on today?"
- Data not adding: Check logs for REST command errors, verify auth token is correct