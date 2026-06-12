import signal
import threading
import time
from datetime import datetime

from hardware import read_sensor, set_buzzer, set_fan, set_pump, setup_hardware
from mqtt_service import MqttService
from mqtt_topics import (
    COMMAND_TOPIC,
    DEVICE_STATE_TOPIC,
    HUMIDITY_TOPIC,
    SENSOR_TOPIC,
    STATUS_TOPIC,
    TEMPERATURE_TOPIC,
)

PUBLISH_INTERVAL_SECONDS = 5
DEVICE_STATUS_SERVICE_NAME = "device-agent"

device_state = {
    "fan": False,
    "pump": False,
    "buzzer": False,
    "updated_at": "",
}

stop_event = threading.Event()
mqtt_service = MqttService(client_id="plant-device-agent")


def publish_device_state():
    """대시보드와 동기화되도록 현재 장치 상태를 MQTT로 발행한다."""
    device_state["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    mqtt_service.publish(DEVICE_STATE_TOPIC, device_state, retain=True)


def publish_sensor_payload(sensor: dict):
    """웹 서비스가 구독하는 MQTT 토픽으로 센서 데이터를 발행한다."""
    measured_at = sensor.get("measured_at")
    mode = sensor.get("mode")

    mqtt_service.publish(
        TEMPERATURE_TOPIC,
        {
            "value": sensor.get("temperature"),
            "measured_at": measured_at,
            "mode": mode,
        },
        retain=True,
    )
    mqtt_service.publish(
        HUMIDITY_TOPIC,
        {
            "value": sensor.get("humidity"),
            "measured_at": measured_at,
            "mode": mode,
        },
        retain=True,
    )
    mqtt_service.publish(
        SENSOR_TOPIC,
        {
            "light": sensor.get("light"),
            "measured_at": measured_at,
            "mode": mode,
        },
        retain=True,
    )
    mqtt_service.publish(
        STATUS_TOPIC,
        {
            "service": DEVICE_STATUS_SERVICE_NAME,
            "connected": True,
            "measured_at": measured_at,
        },
        retain=True,
    )


def handle_command(payload: dict):
    """MQTT 제어 명령을 해석해 로컬 GPIO 장치에 적용한다."""
    name = payload.get("name")
    action = payload.get("action")
    on = action == "on"

    if name == "fan":
        set_fan(on)
        device_state["fan"] = on
    elif name == "pump":
        set_pump(on)
        device_state["pump"] = on
    elif name == "buzzer":
        set_buzzer(on)
        device_state["buzzer"] = on
    else:
        return

    publish_device_state()


def publish_sensor_loop():
    """일정 주기로 하드웨어를 읽고 최신 센서값을 MQTT로 발행한다."""
    while not stop_event.is_set():
        sensor = read_sensor()
        publish_sensor_payload(sensor)
        stop_event.wait(PUBLISH_INTERVAL_SECONDS)


def shutdown(*_args):
    stop_event.set()
    mqtt_service.stop()


def main():
    setup_hardware()
    mqtt_service.subscribe_json(COMMAND_TOPIC, handle_command)
    mqtt_service.start()
    publish_device_state()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    worker = threading.Thread(target=publish_sensor_loop, daemon=True)
    worker.start()

    while not stop_event.is_set():
        time.sleep(0.5)


if __name__ == "__main__":
    main()
