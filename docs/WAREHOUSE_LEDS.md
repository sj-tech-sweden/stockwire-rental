# Warehouse LEDs

> Last reviewed: 2026-08-06

## Overview

The Warehouse LEDs module provides LED controller integration for visual bin highlighting, device locating, and job-based picking guidance.

**Frontend:** WarehouseLedsPage.vue (settings), WarehouseMap.vue (visualization)  
**Backend:** `/api/v1/warehouse-leds/*`  
**Protocol:** MQTT

---

## Features

- **LED Controllers** - Manage ESPHome-based LED controllers
- **Zone Mappings** - Map LEDs to warehouse zones/bins
- **Bin Highlighting** - Highlight specific bins with colors
- **Device Locating** - Flash LED at device location
- **Job Highlighting** - Highlight all bins for a job
- **ESPHome Config** - Generate ESPHome YAML for controllers

---

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   Backend   │────▶│ MQTT Broker │
│  (WebSocket)│     │   (FastAPI) │     │  (Mosquitto)│
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                                        ┌──────▼──────┐
                                        │   ESPHome   │
                                        │ Controllers │
                                        └──────┬──────┘
                                               │
                                        ┌──────▼──────┐
                                        │ LED Strips  │
                                        │  (WS2812B)  │
                                        └─────────────┘
```

---

## Concepts

### LED Controllers

Physical devices that control LED strips:

- ESP32/ESP8266 with ESPHome firmware
- Connected to MQTT broker
- Each controller manages multiple LED zones
- Has IP address for ESPHome API access

### LED Zones

Logical groupings of LEDs on a controller:

- Each zone maps to a warehouse area
- Contains one or more LEDs
- Can be assigned colors

### Bin Mappings

Mapping between warehouse zones and LEDs:

- Links a zone to a specific LED on a controller
- Defines default color
- Enables visual identification

---

## UI Overview

### Controller Management

1. Navigate to Settings → Warehouse LEDs
2. View list of controllers
3. Click "Add Controller" to register new
4. Enter controller details (name, IP, type)
5. Click to configure zones

### Zone Mapping

1. Open controller details
2. Click "Configure Zones"
3. Add zone mappings:
   - Select warehouse zone
   - Enter LED index on controller
   - Set default color
4. Save configuration

### LED Control (Warehouse Map)

1. Navigate to inventory page
2. Open warehouse map view
3. Click zone to highlight
4. Use controls to:
   - Highlight bins
   - Locate device
   - Clear highlights
   - Highlight job bins

### ESPHome Configuration

1. Open controller details
2. Click "Download YAML"
3. Get ESPHome configuration file
4. Flash to ESP32 device

---

## API Endpoints

### Controllers

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/warehouse-leds/controllers` | List controllers |
| `POST` | `/warehouse-leds/controllers` | Create controller |
| `GET` | `/warehouse-leds/controllers/{id}` | Get controller |
| `PATCH` | `/warehouse-leds/controllers/{id}` | Update controller |
| `DELETE` | `/warehouse-leds/controllers/{id}` | Delete controller |
| `GET` | `/warehouse-leds/controllers/{id}/zones` | Get controller zones |
| `PUT` | `/warehouse-leds/controllers/{id}/zones` | Update zones |

### Bin Mappings

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/warehouse-leds/mappings` | List mappings |
| `POST` | `/warehouse-leds/mappings` | Create mapping |
| `PUT` | `/warehouse-leds/mappings/{id}` | Update mapping |
| `DELETE` | `/warehouse-leds/mappings/{id}` | Delete mapping |
| `POST` | `/warehouse-leds/mappings/bulk` | Bulk create |

### LED Control

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/warehouse-leds/highlight` | Highlight bins |
| `POST` | `/warehouse-leds/locate/{device_id}` | Locate device |
| `POST` | `/warehouse-leds/return/{zone_id}` | Return to idle |
| `POST` | `/warehouse-leds/highlight-job/{job_id}` | Highlight job bins |
| `POST` | `/warehouse-leds/clear` | Clear all |
| `POST` | `/warehouse-leds/identify` | Identify controller |

### Status & Config

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/warehouse-leds/status` | Get system status |
| `GET` | `/warehouse-leds/esphome/{id}.yaml` | Get ESPHome YAML |
| `GET` | `/warehouse-leds/esphome/secrets-template` | Get secrets template |

---

## MQTT Topics

### Topic Structure

```
{prefix}/{warehouse_id}/{controller_id}/{command}
```

**Default:** `stockwire/default/{controller_id}/{command}`

### Commands

| Topic | Payload | Description |
|-------|---------|-------------|
| `highlight` | `{"leds": [{"index": 0, "color": "#FF0000"}]}` | Set LED colors |
| `clear` | `{}` | Turn off all LEDs |
| `identify` | `{}` | Flash all LEDs |
| `status` | `{}` | Request status |

### Responses

| Topic | Payload | Description |
|-------|---------|-------------|
| `status/response` | `{"online": true, ...}` | Controller status |

---

## ESPHome Configuration

### Generated YAML

The system generates ESPHome YAML configuration for controllers:

```yaml
esphome:
  name: stockwire-controller-1
  
wifi:
  ssid: !secret wifi_ssid
  password: !secret wifi_password

mqtt:
  broker: !secret mqtt_broker
  topic_prefix: stockwire/default/controller-1

light:
  - platform: neopixelbus
    type: GRB
    variant: WS2812B
    pin: GPIO5
    num_leds: 50
    name: "LED Strip"
```

### Secrets Template

```yaml
wifi_ssid: YourWiFiSSID
wifi_password: YourWiFiPassword
mqtt_broker: mqtt.example.com
mqtt_username: stockwire
mqtt_password: your_mqtt_password
```

---

## Data Model

### LED Controller

```json
{
  "id": "uuid",
  "name": "Main Warehouse Controller",
  "ip_address": "192.168.1.100",
  "type": "esp32",
  "status": "online",
  "zones": [...],
  "created_at": "2026-08-06T10:00:00Z"
}
```

### LED Bin Mapping

```json
{
  "id": "uuid",
  "controller_id": "uuid",
  "zone_id": "uuid",
  "led_index": 5,
  "color": "#00FF00",
  "created_at": "2026-08-06T10:00:00Z"
}
```

---

## Workflow Examples

### Highlighting Bins for a Job

1. Operator selects job in UI
2. Clicks "Highlight Bins"
3. Backend:
   - Queries job requirements
   - Finds linked devices
   - Looks up device locations
   - Gets LED mappings for locations
4. Sends MQTT messages to controllers
5. LEDs light up at bin locations

### Locating a Device

1. Operator searches for device
2. Clicks "Locate" button
3. Backend:
   - Gets device location
   - Finds LED mapping
   - Sends locate command
4. LED flashes at device location
5. Operator clicks "Return" to stop

---

## Hardware Requirements

### Supported Controllers

- ESP32 dev board
- ESP8266 dev board (limited)

### LED Types

- WS2812B (NeoPixel) - Recommended
- SK6812 (RGBW)
- APA102 (SPI)

### Wiring

- LED strip power: 5V or 12V
- Data pin: GPIO5 (configurable)
- Power supply: 5A per 50 LEDs (WS2812B)

---

## Limitations

- No real-time feedback from LEDs
- No brightness control per LED (global only)
- No LED animation effects
- No multi-controller synchronization
- No LED health monitoring
