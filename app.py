import csv
import json
import os
import threading
from datetime import datetime

from flask import Flask, jsonify, redirect, render_template, request
from flask_socketio import SocketIO, emit

from config import ABNORMAL_DURATION_SECONDS, DEFAULT_PLANT_CONFIG
from mqtt_service import MqttService
from mqtt_topics import (
    COMMAND_TOPIC,
    DEVICE_STATE_TOPIC,
    HUMIDITY_TOPIC,
    SENSOR_TOPIC,
    STATUS_TOPIC,
    TEMPERATURE_TOPIC,
)
from notifier import send_notification_once

app = Flask(__name__)
socketio = SocketIO(app, async_mode="threading", cors_allowed_origins="*")

CONFIG_FILE = "plant_config.json"
HISTORY_FILE = "sensor_history.csv"
MAX_HISTORY_ROWS = 500
HISTORY_API_LIMIT = 30
HISTORY_FIELDNAMES = ["measured_at", "temperature", "humidity", "light", "mode"]
MANAGED_DEVICE_NAMES = ("fan", "pump", "buzzer")
VALID_CONTROL_MODES = {"auto", "manual"}

DEFAULT_SENSOR = {
    "temperature": None,
    "humidity": None,
    "light": "unknown",
    "measured_at": "-",
    "mode": "waiting",
}

device_state = {
    "fan": False,
    "pump": False,
    "buzzer": False,
    "control_mode": "auto",
}

abnormal_start_time = None
latest_sensor = DEFAULT_SENSOR.copy()
latest_warnings = []
latest_abnormal = []
latest_device_status = {"service": "device-agent", "connected": False}

state_lock = threading.Lock()
mqtt_service = MqttService(client_id="plant-dashboard-service")
runtime_started = False


def build_status_payload():
    """HTTP 응답과 Socket.IO 이벤트에서 공통으로 사용하는 대시보드 상태를 만든다."""
    config = load_config()
    with state_lock:
        sensor = latest_sensor.copy()
        abnormal = list(latest_abnormal)
        warnings = list(latest_warnings)
        current_status = latest_device_status.copy()

    abnormal_duration = 0
    if abnormal_start_time is not None:
        abnormal_duration = (datetime.now() - abnormal_start_time).total_seconds()

    return {
        "config": config,
        "sensor": sensor,
        "abnormal": abnormal,
        "warnings": warnings,
        "abnormal_duration": int(abnormal_duration),
        "device_state": device_state,
        "mqtt_connected": mqtt_service.connected,
        "device_connected": current_status.get("connected", False),
    }


def emit_realtime_update(include_history: bool = False):
    # MQTT 메시지로 서버 상태를 갱신한 뒤, 최신 상태를 브라우저로 즉시 전송한다.
    socketio.emit("status_update", build_status_payload())
    if include_history:
        socketio.emit(
            "history_update",
            {"history": load_sensor_history(limit=HISTORY_API_LIMIT)},
        )


def ensure_runtime_started():
    """Flask 서비스가 시작될 때 MQTT 구독을 한 번만 초기화한다."""
    global runtime_started
    if runtime_started:
        return

    mqtt_service.subscribe_json(TEMPERATURE_TOPIC, handle_temperature_message)
    mqtt_service.subscribe_json(HUMIDITY_TOPIC, handle_humidity_message)
    mqtt_service.subscribe_json(SENSOR_TOPIC, handle_sensor_message)
    mqtt_service.subscribe_json(DEVICE_STATE_TOPIC, handle_device_state_message)
    mqtt_service.subscribe_json(STATUS_TOPIC, handle_status_message)
    mqtt_service.start()
    runtime_started = True


def handle_temperature_message(payload: dict):
    update_latest_sensor(extract_metric_update(payload, "temperature"))


def handle_humidity_message(payload: dict):
    update_latest_sensor(extract_metric_update(payload, "humidity"))


def handle_sensor_message(sensor: dict):
    global latest_sensor, latest_warnings, latest_abnormal

    sensor = update_latest_sensor(sensor)

    append_sensor_history(sensor)

    config = load_config()
    abnormal, warnings = analyze_status(sensor, config)
    apply_auto_control(sensor, config, abnormal)

    with state_lock:
        latest_warnings = warnings
        latest_abnormal = abnormal

    emit_realtime_update(include_history=True)


def handle_device_state_message(payload: dict):
    with state_lock:
        for name in MANAGED_DEVICE_NAMES:
            if name in payload:
                device_state[name] = bool(payload[name])

    emit_realtime_update()


def handle_status_message(payload: dict):
    global latest_device_status
    with state_lock:
        latest_device_status = payload

    emit_realtime_update()


def normalize_sensor(sensor: dict):
    normalized = DEFAULT_SENSOR.copy()
    normalized.update(sensor)
    return normalized


def extract_metric_update(payload: dict, field_name: str):
    return {
        field_name: payload.get("value"),
        "measured_at": payload.get("measured_at"),
        "mode": payload.get("mode"),
    }


def update_latest_sensor(sensor_update: dict):
    global latest_sensor

    with state_lock:
        merged = latest_sensor.copy()
        merged.update(sensor_update)
        latest_sensor = normalize_sensor(merged)
        return latest_sensor.copy()


def load_config():
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_PLANT_CONFIG)

    with open(CONFIG_FILE, "r", encoding="utf-8") as file:
        config = json.load(file)

    return ensure_config_defaults(config)


def ensure_config_defaults(config):
    merged = DEFAULT_PLANT_CONFIG.copy()
    merged.update(config)
    return merged


def save_config(config):
    normalized_config = ensure_config_defaults(config)
    with open(CONFIG_FILE, "w", encoding="utf-8") as file:
        json.dump(normalized_config, file, ensure_ascii=False, indent=2)


def ensure_history_file():
    if os.path.exists(HISTORY_FILE):
        return

    with open(HISTORY_FILE, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=HISTORY_FIELDNAMES)
        writer.writeheader()


def append_sensor_history(sensor):
    ensure_history_file()

    with open(HISTORY_FILE, "a", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=HISTORY_FIELDNAMES)
        writer.writerow(
            {
                "measured_at": sensor.get("measured_at", ""),
                "temperature": sensor.get("temperature", ""),
                "humidity": sensor.get("humidity", ""),
                "light": sensor.get("light", "unknown"),
                "mode": sensor.get("mode", "unknown"),
            }
        )

    trim_sensor_history()


def trim_sensor_history():
    with open(HISTORY_FILE, "r", encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    if len(rows) <= MAX_HISTORY_ROWS:
        return

    rows = rows[-MAX_HISTORY_ROWS:]
    with open(HISTORY_FILE, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=HISTORY_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def load_sensor_history(limit=HISTORY_API_LIMIT):
    ensure_history_file()

    with open(HISTORY_FILE, "r", encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    recent_rows = rows[-limit:]
    history = []
    for row in recent_rows:
        history.append(
            {
                "measured_at": row["measured_at"],
                "temperature": _to_float_or_none(row["temperature"]),
                "humidity": _to_float_or_none(row["humidity"]),
                "light": row["light"] or "unknown",
                "mode": row["mode"] or "unknown",
            }
        )

    return history


def _to_float_or_none(value):
    if value in ("", None, "None"):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def analyze_status(sensor, config):
    abnormal = []
    warnings = []

    if sensor["temperature"] is None or sensor["humidity"] is None:
        return ["sensor"], ["센서 값을 읽지 못했습니다. 배선 또는 센서 상태를 확인해 주세요."]

    temp = float(sensor["temperature"])
    humidity = float(sensor["humidity"])

    if temp < float(config["min_temp"]):
        abnormal.append("temperature")
        warnings.append("온도가 기준보다 낮습니다.")
    elif temp > float(config["max_temp"]):
        abnormal.append("temperature")
        warnings.append("온도가 기준보다 높습니다.")

    if humidity < float(config["min_humidity"]):
        abnormal.append("humidity")
        warnings.append("습도가 기준보다 낮습니다.")
    elif humidity > float(config["max_humidity"]):
        abnormal.append("humidity")
        warnings.append("습도가 기준보다 높습니다.")

    if sensor["light"] != "unknown" and sensor["light"] != config["light_required"]:
        abnormal.append("light")
        warnings.append("조도가 기준과 맞지 않습니다.")

    return abnormal, warnings


def apply_auto_control(sensor, config, abnormal):
    global abnormal_start_time

    now = datetime.now()
    abnormal_required = int(config["abnormal_duration_seconds"])

    if len(abnormal) >= 2:
        if abnormal_start_time is None:
            abnormal_start_time = now
    else:
        abnormal_start_time = None

    abnormal_duration = 0
    if abnormal_start_time is not None:
        abnormal_duration = (now - abnormal_start_time).total_seconds()

    if device_state["control_mode"] == "auto":
        fan_on = sensor["temperature"] is not None and float(sensor["temperature"]) > float(config["max_temp"])
        buzzer_on = len(abnormal) >= 2 and abnormal_duration >= abnormal_required

        previous_fan = device_state["fan"]
        previous_buzzer = device_state["buzzer"]

        publish_device_command("fan", fan_on)
        publish_device_command("pump", False)
        publish_device_command("buzzer", buzzer_on)

        plant_name = config.get("plant_name", "식물")

        if fan_on and not previous_fan:
            send_notification_once(
                "fan_on",
                f"[{plant_name}] 팬 자동 작동",
                (
                    "온도가 기준보다 높아 팬이 자동으로 켜졌습니다.\n\n"
                    f"현재 온도: {sensor['temperature']}°C\n"
                    f"기준 최대 온도: {config['max_temp']}°C"
                ),
            )

        if buzzer_on and not previous_buzzer:
            send_notification_once(
                "buzzer_on",
                f"[{plant_name}] 생장 환경 경고",
                (
                    "비정상 생장 환경이 지속되어 부저가 작동했습니다.\n\n"
                    f"비정상 항목 수: {len(abnormal)}개\n"
                    f"지속 시간: {int(abnormal_duration)}초\n"
                    f"경보 기준: {abnormal_required}초"
                ),
            )

    return abnormal_duration


def publish_device_command(name: str, on: bool):
    mqtt_service.publish(
        COMMAND_TOPIC,
        {
            "name": name,
            "action": "on" if on else "off",
            "requested_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
    )


def build_device_state_payload():
    return {name: device_state[name] for name in MANAGED_DEVICE_NAMES}


def apply_device_action(name: str, action: str):
    on = action == "on"
    device_state["control_mode"] = "manual"
    device_state[name] = on

    publish_device_command(name, on)
    threading.Thread(
        target=notify_manual_device_action,
        args=(name, action),
        daemon=True,
    ).start()

    emit_realtime_update()
    return on


def notify_manual_device_action(name: str, action: str):
    device_name_ko = {
        "fan": "팬",
        "pump": "펌프",
        "buzzer": "부저",
    }

    send_notification_once(
        f"manual_{name}_{action}",
        f"[수동 제어] {device_name_ko[name]} {'ON' if action == 'on' else 'OFF'}",
        f"웹 UI에서 {device_name_ko[name]} 장치가 수동으로 {'ON' if action == 'on' else 'OFF'} 처리되었습니다.",
    )


def update_system_once():
    ensure_runtime_started()
    payload = build_status_payload()
    return (
        payload["config"],
        payload["sensor"],
        payload["abnormal"],
        payload["warnings"],
        payload["abnormal_duration"],
    )


@socketio.on("connect")
def handle_socket_connect():
    ensure_runtime_started()
    emit("status_update", build_status_payload())
    emit("history_update", {"history": load_sensor_history(limit=HISTORY_API_LIMIT)})


@app.route("/")
def index():
    config, sensor, abnormal, warnings, abnormal_duration = update_system_once()

    return render_template(
        "index.html",
        config=config,
        sensor=sensor,
        abnormal=abnormal,
        warnings=warnings,
        abnormal_duration=int(abnormal_duration),
        abnormal_required=int(config["abnormal_duration_seconds"]),
        device_state=device_state,
        history_limit=HISTORY_API_LIMIT,
        mqtt_connected=mqtt_service.connected,
        device_connected=latest_device_status.get("connected", False),
    )


@app.route("/config", methods=["POST"])
def update_config():
    config = {
        "plant_name": request.form.get("plant_name", "식물"),
        "min_temp": float(request.form.get("min_temp", 20)),
        "max_temp": float(request.form.get("max_temp", 28)),
        "min_humidity": float(request.form.get("min_humidity", 40)),
        "max_humidity": float(request.form.get("max_humidity", 70)),
        "light_required": request.form.get("light_required", "bright"),
        "abnormal_duration_seconds": int(request.form.get("abnormal_duration_seconds", ABNORMAL_DURATION_SECONDS)),
    }

    save_config(config)
    emit_realtime_update()
    return redirect("/")


@app.route("/mode/<mode>")
def change_mode(mode):
    if mode in VALID_CONTROL_MODES:
        device_state["control_mode"] = mode
        emit_realtime_update()
    return redirect("/")


@app.route("/api/mode/<mode>")
def api_change_mode(mode):
    if mode not in VALID_CONTROL_MODES:
        return jsonify({"ok": False, "message": "invalid mode"}), 400

    device_state["control_mode"] = mode
    emit_realtime_update()
    return jsonify(
        {
            "ok": True,
            "control_mode": device_state["control_mode"],
            "device_state": build_device_state_payload(),
        }
    )


@app.route("/device/<name>/<action>")
def control_device(name, action):
    if name not in MANAGED_DEVICE_NAMES or action not in {"on", "off"}:
        return redirect("/")

    apply_device_action(name, action)
    return redirect("/")


@app.route("/api/device/<name>/<action>")
def api_control_device(name, action):
    if name not in MANAGED_DEVICE_NAMES:
        return jsonify({"ok": False, "message": "invalid device"}), 400
    if action not in {"on", "off"}:
        return jsonify({"ok": False, "message": "invalid action"}), 400

    apply_device_action(name, action)
    return jsonify(
        {
            "ok": True,
            "control_mode": device_state["control_mode"],
            "device": name,
            "action": action,
            "device_state": build_device_state_payload(),
        }
    )


@app.route("/api/status")
def api_status():
    return jsonify(build_status_payload())


@app.route("/api/history")
def api_history():
    limit = request.args.get("limit", default=HISTORY_API_LIMIT, type=int)
    if limit <= 0:
        limit = HISTORY_API_LIMIT
    limit = min(limit, MAX_HISTORY_ROWS)

    return jsonify({"history": load_sensor_history(limit=limit)})


if __name__ == "__main__":
    ensure_runtime_started()
    ensure_history_file()
    socketio.run(app, host="0.0.0.0", port=5000, debug=True, use_reloader=False)
