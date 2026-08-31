# API Reference

## Base URL
{{scheme}}://{{host}}/{{base-path}}

## Authentication
{{auth mechanism, e.g., Bearer token, API key}}

## Endpoints

### GET {{/path}}
- **Description:** {{what it does}}
- **Query params:** {{name (type, required, description)}}
- **Response 200:**
```json
{{example}}
```
- **Errors:** {{status — meaning}}

### POST {{/path}}
- **Description:** {{what it does}}
- **Request body:**
```json
{{example}}
```
- **Response 201:**
```json
{{example}}
```
- **Errors:** {{status — meaning}}

## Error Response Format
```json
{
  "error": {
    "code": "{{error_code}}",
    "message": "{{human-readable message}}"
  }
}
```

## Rate Limits
{{limits, if any}}
