# app.py

from flask import Flask, render_template, request, redirect, jsonify
import json
import os
from datetime import datetime

from config import DEFAULT_PLANT_CONFIG, ABNORMAL_DURATION_SECONDS
from hardware import setup_hardware, read_sensor, set_fan, set_pump, set_buzzer

app = Flask(__name__)

CONFIG_FILE = "plant_config.json"

device_state = {
    "fan": False,
    "pump": False,
    "buzzer": False,
    "control_mode": "auto"
}

abnormal_start_time = None
latest_sensor = None
latest_warnings = []
latest_abnormal = []


def load_config():
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_PLANT_CONFIG)

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def analyze_status(sensor, config):
    abnormal = []
    warnings = []

    if sensor["temperature"] is None or sensor["humidity"] is None:
        return ["sensor"], ["센서값을 읽지 못했습니다. 배선 또는 센서 상태를 확인하세요."]

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
        pump_on = sensor["humidity"] is not None and float(sensor["humidity"]) < float(config["min_humidity"])
        buzzer_on = len(abnormal) >= 2 and abnormal_duration >= ABNORMAL_DURATION_SECONDS

        device_state["fan"] = fan_on
        device_state["pump"] = pump_on
        device_state["buzzer"] = buzzer_on

        set_fan(fan_on)
        set_pump(pump_on)
        set_buzzer(buzzer_on)

    return abnormal_duration


def update_system_once():
    global latest_sensor, latest_warnings, latest_abnormal

    config = load_config()
    sensor = read_sensor()
    abnormal, warnings = analyze_status(sensor, config)
    abnormal_duration = apply_auto_control(sensor, config, abnormal)

    latest_sensor = sensor
    latest_warnings = warnings
    latest_abnormal = abnormal

    return config, sensor, abnormal, warnings, abnormal_duration


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
        abnormal_required=ABNORMAL_DURATION_SECONDS,
        device_state=device_state
    )


@app.route("/config", methods=["POST"])
def update_config():
    config = {
        "plant_name": request.form.get("plant_name", "식물"),
        "min_temp": float(request.form.get("min_temp", 20)),
        "max_temp": float(request.form.get("max_temp", 28)),
        "min_humidity": float(request.form.get("min_humidity", 40)),
        "max_humidity": float(request.form.get("max_humidity", 70)),
        "light_required": request.form.get("light_required", "bright")
    }

    save_config(config)
    return redirect("/")


@app.route("/mode/<mode>")
def change_mode(mode):
    if mode in ["auto", "manual"]:
        device_state["control_mode"] = mode
    return redirect("/")


@app.route("/device/<name>/<action>")
def control_device(name, action):
    on = action == "on"

    device_state["control_mode"] = "manual"

    if name == "fan":
        device_state["fan"] = on
        set_fan(on)
    elif name == "pump":
        device_state["pump"] = on
        set_pump(on)
    elif name == "buzzer":
        device_state["buzzer"] = on
        set_buzzer(on)

    return redirect("/")


@app.route("/api/status")
def api_status():
    config, sensor, abnormal, warnings, abnormal_duration = update_system_once()

    return jsonify({
        "config": config,
        "sensor": sensor,
        "abnormal": abnormal,
        "warnings": warnings,
        "abnormal_duration": int(abnormal_duration),
        "device_state": device_state
    })


if __name__ == "__main__":
    setup_hardware()
    app.run(host="0.0.0.0", port=5000, debug=True)