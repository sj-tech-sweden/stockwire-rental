"""ESPHome YAML config generator for LED controllers."""

from __future__ import annotations

from textwrap import dedent


def generate_esphome_yaml(
    controller_id: str,
    led_count: int = 300,
    led_pin: int = 5,
    mqtt_broker: str = "localhost",
    mqtt_port: int = 1883,
    mqtt_username: str = "",
    mqtt_password: str = "",
    mqtt_topic_prefix: str = "stockwire",
    wifi_ssid: str = "YOUR_WIFI_SSID",
    wifi_password: str = "YOUR_WIFI_PASSWORD",
    ota_password: str = "",
    api_key: str = "",
) -> str:
    topic_suffix = controller_id
    command_topic = f"{mqtt_topic_prefix}/{topic_suffix}/cmd"
    status_topic = f"{mqtt_topic_prefix}/{topic_suffix}/status"

    mqtt_section = ""
    if mqtt_username:
        mqtt_section = f"""
    username: "{mqtt_username}"
    password: "{mqtt_password}" """

    ota_section = ""
    if ota_password:
        ota_section = f"""
  - platform: wifi
    password: "{ota_password}" """

    api_section = ""
    if api_key:
        api_section = f"""
api:
  encryption:
    key: "{api_key}"
"""

    return dedent(f"""\
    esphome:
      name: {controller_id}
      friendly_name: "Stockwire LED {controller_id}"
      project:
        name: "stockwire.led-controller"
        version: "1.0.0"

    esp32:
      board: esp32dev

    wifi:
      ssid: "{wifi_ssid}"
      password: "{wifi_password}"
      fast_connect: true

      ap:
        ssid: "{controller_id}-fallback"
        password: "stockwire123"

    captive_portal:

    logger:
      level: INFO

    mqtt:
      broker: "{mqtt_broker}"
      port: {mqtt_port}{mqtt_section}
      topic_prefix: "{mqtt_topic_prefix}"

    {api_section}
    ota:
      - platform: esphome
        password: "{ota_password}" if ota_password else ""

    web_server:
      port: 80

    status_led:
      pin:
        number: GPIO2
        inverted: true

    output:
      - platform: ledc
        id: led_output_{led_pin}
        pin: GPIO{led_pin}

    light:
      - platform: monochromatic
        name: "LED Strip"
        output: led_output_{led_pin}
        gamma_correct: 2.8

    sensor:
      - platform: wifi_signal
        name: "WiFi Signal"
        update_interval: 60s

      - platform: uptime
        name: "Uptime"

    text_sensor:
      - platform: wifi_info
        ip_address:
          name: "IP Address"
        mac_address:
          name: "MAC Address"

    switch:
      - platform: gpio
        name: "Status LED"
        pin: GPIO2
        inverted: true
        id: status_led

    interval:
      - interval: 15s
        then:
          - mqtt.publish:
              topic: "{status_topic}"
              payload: !lambda |-
                char buf[512];
                snprintf(buf, sizeof(buf),
                  "{{{{\\"status\\": \\"online\\", \\"controller_id\\": \\"{controller_id}\\", \\"led_count\\": {led_count}}}}}");
                return std::string(buf);
    """).strip()


def generate_secrets_template() -> str:
    return dedent("""\
        // ==========================================
        // Stockwire Rental - ESPHome LED Controller
        // ==========================================
        // Copy this file to secrets.h and fill in your values.
        // Do NOT commit secrets.h to version control.

        // WiFi
        #define WIFI_SSID "YourWiFiSSID"
        #define WIFI_PASS "YourWiFiPassword"

        // MQTT Broker
        #define MQTT_HOST "mqtt.example.com"
        #define MQTT_PORT 1883
        #define MQTT_USER "mqtt_user"
        #define MQTT_PASS "mqtt_password"

        // Stockwire Configuration
        #define TOPIC_PREFIX "stockwire"
        #define WAREHOUSE_ID "default"

        // LED Configuration
        #define LED_PIN 5
        #define LED_LENGTH 300

        // Controller (auto-generated from MAC if not set)
        // #define CONTROLLER_ID "esp-custom-id"
        // #define TOPIC_SUFFIX "custom-topic"
    """).strip()
