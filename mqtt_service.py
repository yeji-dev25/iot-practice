import json
import threading
from typing import Callable

import paho.mqtt.client as mqtt

from config import MQTT_BROKER_HOST, MQTT_BROKER_PORT, MQTT_PASSWORD, MQTT_USERNAME


class MqttService:
    def __init__(self, client_id: str):
        """두 서버 프로세스에서 공통으로 사용하는 MQTT 클라이언트 래퍼."""
        self.client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)
        self._connected = False
        self._started = False
        self._subscriptions: list[tuple[str, int]] = []
        self._handlers: dict[str, Callable[[dict], None]] = {}
        self._lock = threading.Lock()

        if MQTT_USERNAME:
            self.client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

    @property
    def connected(self) -> bool:
        return self._connected

    def start(self):
        """MQTT 백그라운드 루프를 한 번만 시작한다."""
        with self._lock:
            if self._started:
                return
            self._started = True

        self.client.connect_async(MQTT_BROKER_HOST, MQTT_BROKER_PORT, keepalive=60)
        self.client.loop_start()

    def stop(self):
        """프로세스 종료 시 MQTT 네트워크 루프를 정리한다."""
        with self._lock:
            if not self._started:
                return
            self._started = False

        self.client.loop_stop()
        self.client.disconnect()

    def publish(self, topic: str, payload: dict, retain: bool = False):
        message = json.dumps(payload, ensure_ascii=False)
        self.client.publish(topic, message, retain=retain)

    def subscribe_json(self, topic: str, handler: Callable[[dict], None], qos: int = 0):
        """JSON payload를 해석해서 전달하는 토픽 핸들러를 등록한다."""
        self._handlers[topic] = handler
        self._subscriptions.append((topic, qos))
        if self._connected:
            self.client.subscribe(topic, qos=qos)

    def _on_connect(self, client, userdata, flags, reason_code):
        self._connected = True
        for topic, qos in self._subscriptions:
            client.subscribe(topic, qos=qos)

    def _on_disconnect(self, client, userdata, *args):
        self._connected = False

    def _on_message(self, client, userdata, message):
        # 잘못된 payload 하나 때문에 서비스 전체가 멈추지 않도록 무시한다.
        handler = self._handlers.get(message.topic)
        if handler is None:
            return

        try:
            payload = json.loads(message.payload.decode("utf-8"))
        except Exception:
            return

        handler(payload)
