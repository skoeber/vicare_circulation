# ViCare Circulation

Home Assistant custom integration for selecting fixed domestic hot water circulation schedules through the Viessmann Climate Solutions API.

Home Assistant 2025.1 or newer is required.

The integration writes the complete `heating.dhw.pumps.circulation.schedule`. It does not directly switch the pump and does not replace the official ViCare integration.

## Presets

| Preset | Monday-Friday | Saturday-Sunday |
|---|---|---|
| `Standard` | 17:00-22:00 | 07:30-23:00 |
| `Ganztägig` | 00:00-24:00 | 00:00-24:00 |
| `Aus` | Off | Off |

## Installation

### HACS

1. Add this repository to HACS as a custom integration repository.
2. Install **ViCare Circulation**.
3. Restart Home Assistant.

### Manual

Copy `custom_components/vicare_circulation` into the `custom_components` directory of the Home Assistant configuration and restart Home Assistant.

## OAuth client

1. Sign in to the [Viessmann Developer Portal](https://app.developer.viessmann-climatesolutions.com) with the account used by ViCare.
2. Create a dedicated API client.
3. Add this exact redirect URI:

   ```text
   https://my.home-assistant.io/redirect/oauth
   ```

4. Disable reCAPTCHA for the client if the portal offers that option.
5. In Home Assistant, open **Settings > Devices & services > Application credentials**.
6. Add credentials for **ViCare Circulation**. Enter the Viessmann client ID. The client secret is ignored by Viessmann; enter any non-empty placeholder.
7. Add the **ViCare Circulation** integration and complete the OAuth login.

The integration requests `IoT User offline_access` and uses Authorization Code with PKCE (S256). ViCare credentials and OAuth tokens are not exposed as entity attributes.

## Entities

- Select: chooses `Standard`, `Ganztägig`, or `Aus`.
- Binary sensor: reports the actual pump status returned by Viessmann.
- Status sensor: reports the matching preset or `Benutzerdefiniert` for a schedule changed elsewhere.
- API schedule sensor: disabled by default; exposes the sanitized schedule as an attribute.

When the API schedule does not match a preset, the select has no current option. Selecting a preset intentionally replaces the complete existing schedule.

## Automation examples

```yaml
alias: Zirkulation bei Urlaub ausschalten
triggers:
  - trigger: state
    entity_id: input_boolean.urlaub
    to: "on"
actions:
  - action: select.select_option
    target:
      entity_id: select.viessmann_warmwasser_zirkulation_zeitplan
    data:
      option: Aus
mode: single
```

```yaml
alias: Standardplan bei Anwesenheit setzen
triggers:
  - trigger: state
    entity_id: input_boolean.anwesend
    to: "on"
actions:
  - action: select.select_option
    target:
      entity_id: select.viessmann_warmwasser_zirkulation_zeitplan
    data:
      option: Standard
mode: single
```

## Troubleshooting

- OAuth errors: verify that the redirect URI matches exactly and that the application credential contains the correct client ID.
- Unavailable entities: verify that Vitoconnect is online and that the circulation schedule remains enabled in ViCare.
- HTTP 429: wait for the next five-minute update. The integration does not aggressively retry rate-limited requests.
- `Benutzerdefiniert`: the current ViCare schedule differs from all three fixed presets. It is not changed until a preset is explicitly selected.

This integration only changes circulation schedules. It makes no statement about hygienic requirements or legionella protection for the drinking-water installation.
