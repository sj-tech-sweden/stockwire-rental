"""MQTT client service for communicating with ESPHome LED controllers."""

from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any

import paho.mqtt.client as mqtt

from app.config import settings

logger = logging.getLogger(__name__)

_client: mqtt.Client | None = None
_lock = threading.Lock()
_status_cache: dict[str, dict[str, Any]] = {}


def _topic(suffix: str) -> str:
    return f"{settings.mqtt_topic_prefix}/{suffix}"


def get_client() -> mqtt.Client | None:
    return _client


def get_controller_status(controller_id: str) -> dict[str, Any] | None:
    return _status_cache.get(controller_id)


def get_all_statuses() -> dict[str, dict[str, Any]]:
    return dict(_status_cache)


def _on_connect(client: mqtt.Client, userdata: Any, flags: dict, rc: int, properties: Any = None) -> None:
    if rc == 0:
        logger.info("MQTT connected to %s:%s", settings.mqtt_broker_host, settings.mqtt_broker_port)
        status_topic = _topic("+/status")
        client.subscribe(status_topic)
        logger.info("Subscribed to %s", status_topic)
    else:
        logger.error("MQTT connection failed with code %s", rc)


def _on_disconnect(client: mqtt.Client, userdata: Any, rc: int, properties: Any = None) -> None:
    logger.warning("MQTT disconnected (rc=%s), will auto-reconnect", rc)


def _on_message(client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
    try:
        parts = msg.topic.split("/")
        if len(parts) >= 2 and parts[-1] == "status":
            controller_id = parts[-2]
            payload = json.loads(msg.payload.decode())
            _status_cache[controller_id] = payload
            logger.debug("Status update from %s: %s", controller_id, payload.get("status"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        logger.warning("Failed to parse MQTT message on %s: %s", msg.topic, exc)


def start_mqtt_client() -> None:
    global _client
    if not settings.mqtt_enabled:
        logger.info("MQTT is disabled (MQTT_ENABLED=false)")
        return

    with _lock:
        if _client is not None:
            return

        client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"stockwire-backend-{int(time.time())}",
        )

        if settings.mqtt_username:
            client.username_pw_set(settings.mqtt_username, settings.mqtt_password)

        if settings.mqtt_tls:
            client.tls_set()

        client.on_connect = _on_connect
        client.on_disconnect = _on_disconnect
        client.on_message = _on_message

        client.reconnect_delay_set(min_delay=1, max_delay=30)

        try:
            client.connect(settings.mqtt_broker_host, settings.mqtt_broker_port, keepalive=60)
        except Exception as exc:
            logger.error("Failed to connect to MQTT broker: %s", exc)
            return

        client.loop_start()
        _client = client
        logger.info("MQTT client started")


def stop_mqtt_client() -> None:
    global _client
    with _lock:
        if _client is not None:
            _client.loop_stop()
            _client.disconnect()
            _client = None
            logger.info("MQTT client stopped")


def publish_command(controller_id: str, payload: dict[str, Any]) -> bool:
    if _client is None:
        logger.warning("MQTT client not connected, cannot publish to %s", controller_id)
        return False

    suffix = controller_id
    topic = _topic(f"{suffix}/cmd")
    payload["warehouse_id"] = settings.mqtt_warehouse_id

    try:
        info = _client.publish(topic, json.dumps(payload), qos=1)
        logger.info("Published command to %s: op=%s", topic, payload.get("op"))
        return info.rc == mqtt.MQTT_ERR_SUCCESS
    except Exception as exc:
        logger.error("Failed to publish to %s: %s", topic, exc)
        return False


def publish_highlight(
    controller_id: str,
    shelves: list[dict[str, Any]],
    color: str = "#FF6600",
    pattern: str = "solid",
    intensity: int = 180,
) -> bool:
    payload = {
        "op": "highlight",
        "shelves": shelves,
        "color": color,
        "pattern": pattern,
        "intensity": intensity,
    }
    return publish_command(controller_id, payload)


def publish_clear(controller_id: str) -> bool:
    return publish_command(controller_id, {"op": "clear"})


def publish_identify(controller_id: str, color: str = "#FFFFFF", duration_seconds: int = 3) -> bool:
    payload = {
        "op": "identify",
        "color": color,
        "duration_seconds": duration_seconds,
    }
    return publish_command(controller_id, payload)


def publish_locate(
    controller_id: str,
    shelf_label: str,
    bin_label: str,
    pixels: list[int],
    color: str = "#FF0000",
    pattern: str = "breathe",
) -> bool:
    payload = {
        "op": "highlight",
        "shelves": [
            {
                "shelf_id": shelf_label,
                "bins": [
                    {
                        "bin_id": bin_label,
                        "pixels": pixels,
                        "color": color,
                        "pattern": pattern,
                    }
                ],
            }
        ],
        "color": color,
        "pattern": pattern,
        "intensity": 180,
    }
    return publish_command(controller_id, payload)
