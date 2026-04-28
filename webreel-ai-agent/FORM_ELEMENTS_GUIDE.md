# Form Elements Guide for Webreel

This guide documents best practices for handling form elements in webreel configs, based on testing and debugging.

## Select Dropdown

Use the native `select` action with selector and value:

```json
{
  "action": "select",
  "selector": "#select-department",
  "value": "IT",
  "description": "Select IT department"
}
```

**Notes:**
- Value is set directly via JavaScript (no visual dropdown opening)
- Works reliably in headless mode
- Triggers proper change events

**Alternative (visual but unreliable):**
```json
{
  "action": "click",
  "selector": "#select-department"
},
{
  "action": "click",
  "selector": "#select-department option[value='IT']"
}
```
This approach shows the dropdown opening but clicking options is unreliable in headless Chrome.

## Radio Buttons

Use standard click action:

```json
{
  "action": "click",
  "selector": "#radio-male",
  "description": "Select male"
}
```

**Notes:**
- Works reliably with direct click
- No special handling needed

## Checkboxes

Use Space key instead of click to avoid double-click issues:

```json
{
  "action": "moveTo",
  "selector": "#checkbox-commit"
},
{
  "action": "key",
  "key": " ",
  "target": "#checkbox-commit",
  "label": "✓",
  "description": "Check commit checkbox"
}
```

**Why Space key?**
- Click action dispatches multiple events (pointerdown, mousedown, pointerup, mouseup, click)
- This can cause checkbox to toggle twice (check then uncheck)
- Space key is the standard keyboard interaction and works reliably
- Use `label: "✓"` to show a checkmark instead of "Space" in the HUD

**Parser Implementation:**
The `bu_to_webreel.py` parser automatically detects checkboxes and converts clicks to Space key actions.

## Text Inputs

Standard click + type pattern:

```json
{
  "action": "click",
  "selector": "#input-username",
  "description": "Focus username"
},
{
  "action": "type",
  "text": "admin"
}
```

## Complete Form Example

```json
{
  "$schema": "https://webreel.dev/schema/v1.json",
  "videos": {
    "form_demo": {
      "url": "http://example.com/form",
      "viewport": {
        "width": 1920,
        "height": 1080
      },
      "steps": [
        {
          "action": "click",
          "selector": "#input-name"
        },
        {
          "action": "type",
          "text": "John Doe"
        },
        {
          "action": "select",
          "selector": "#select-country",
          "value": "US"
        },
        {
          "action": "click",
          "selector": "#radio-gender-male"
        },
        {
          "action": "moveTo",
          "selector": "#checkbox-terms"
        },
        {
          "action": "key",
          "key": " ",
          "target": "#checkbox-terms",
          "label": "✓"
        },
        {
          "action": "click",
          "selector": "#btn-submit"
        }
      ]
    }
  }
}
```

## Browser-Use Integration

The `bu_to_webreel.py` parser handles these conversions automatically:

- `select_dropdown` → `select` action
- `click` on checkbox → `moveTo` + `key " "` with label "✓"
- `click` on other elements → standard `moveTo` + `click`

## Troubleshooting

### Checkbox not staying checked
- Use Space key instead of click
- Ensure no duplicate click events

### Select dropdown not working
- Use `select` action, not click on options
- Verify the value matches an option value attribute

### Form validation failing
- Check that all required fields are filled
- Verify select dropdowns have valid values
- Ensure checkboxes are properly checked
