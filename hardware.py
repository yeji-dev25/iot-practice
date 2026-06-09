import random
from datetime import datetime
from config import (
    SENSOR_MODE,
    DHT_TYPE,
    DHT_PIN,
    LIGHT_PIN,
    FAN_PIN,
    PUMP_PIN,
    BUZZER_PIN,
    RELAY_ACTIVE_LOW
)

_real_ready = False

fan_device = None
pump_device = None
buzzer_device = None
light_device = None
dht_device = None


def setup_hardware(initialize_outputs: bool = True):
    global _real_ready
    global fan_device, pump_device, buzzer_device, light_device, dht_device

    if SENSOR_MODE != "real":
        print("[INFO] MOCK 모드로 실행됩니다.")
        return

    try:
        from gpiozero import OutputDevice
        import RPi.GPIO as GPIO
        import board
        import adafruit_dht

        pin_map = {
            4: board.D4,
            17: board.D17,
            27: board.D27,
            22: board.D22,
            23: board.D23
        }

        dht_pin = pin_map[DHT_PIN]

        if DHT_TYPE == "DHT22":
            dht_device = adafruit_dht.DHT22(dht_pin)
        else:
            dht_device = adafruit_dht.DHT11(dht_pin)

        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(LIGHT_PIN, GPIO.IN)
        light_device = GPIO

        if initialize_outputs:
            # active_high=False면 LOW일 때 ON인 릴레이 대응
            fan_device = OutputDevice(FAN_PIN, active_high=not RELAY_ACTIVE_LOW, initial_value=False)
            pump_device = OutputDevice(PUMP_PIN, active_high=not RELAY_ACTIVE_LOW, initial_value=False)
            buzzer_device = OutputDevice(BUZZER_PIN, active_high=True, initial_value=False)
        else:
            fan_device = None
            pump_device = None
            buzzer_device = None

        _real_ready = True
        print("[INFO] 실제 하드웨어 모드 초기화 완료")

    except Exception as e:
        print("[ERROR] 하드웨어 초기화 실패:", e)
        print("[INFO] 하드웨어 오류로 MOCK처럼 동작합니다.")
        _real_ready = False


def read_sensor():
    if SENSOR_MODE == "real" and _real_ready:
        return read_real_sensor()
    return read_mock_sensor()


def read_mock_sensor():
    return {
        "temperature": round(random.uniform(18, 35), 1),
        "humidity": round(random.uniform(25, 80), 1),
        "light": random.choice(["bright", "dark"]),
        "measured_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "mock"
    }


def read_real_sensor():
    temperature = None
    humidity = None
    light = "unknown"
    errors = []

    try:
        temperature = dht_device.temperature
        humidity = dht_device.humidity

        if temperature is None or humidity is None:
            raise RuntimeError("DHT 센서값이 None입니다.")

        temperature = round(float(temperature), 1)
        humidity = round(float(humidity), 1)
    except Exception as e:
        errors.append(f"DHT: {e}")

    try:
        # 조도센서 DO 기준
        # 모듈마다 HIGH/LOW 의미가 반대일 수 있음
        # 웹에서 조도 상태가 반대로 나오면 여기 bright/dark만 바꾸면 됨
        light_value = light_device.input(LIGHT_PIN)
        light = "bright" if light_value == 1 else "dark"
    except Exception as e:
        errors.append(f"LIGHT: {e}")

    if errors:
        print("[WARN] 센서 읽기 실패:", " | ".join(errors))

    return {
        "temperature": temperature,
        "humidity": humidity,
        "light": light,
        "measured_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "real" if not errors else "real-error"
    }


def set_fan(on: bool):
    _set_output(fan_device, on, "fan")


def set_pump(on: bool):
    _set_output(pump_device, on, "pump")


def set_buzzer(on: bool):
    _set_output(buzzer_device, on, "buzzer")


def _set_output(device, on: bool, name: str):
    if SENSOR_MODE == "real" and _real_ready and device is not None:
        if on:
            device.on()
        else:
            device.off()
    else:
        print(f"[MOCK] {name} {'ON' if on else 'OFF'}")
