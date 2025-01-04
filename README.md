# Beeminder Home Assistant Custom Integration

1. Clone this repository as a folder called `beeminder` in your custom_components folder (if you don't have that, create one where your `configuration.yaml` is)
2. Add this to your configuration.yaml
```
beeminder:
  username: !secret beeminder_username
  auth_token: !secret beeminder_token
```
3. Add `beeminder_username` and `beeminder_token` in secrets.yaml (generate an auth token via Beeminder UI).
4. Restart home assistant.
5. Beeminder goals should show up as sensors.
