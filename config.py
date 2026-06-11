import os

from dotenv import load_dotenv

load_dotenv()

# "mock"이면 가짜 센서값 사용
# "real"이면 실제 라즈베리파이 GPIO 사용
SENSOR_MODE = "real"

# DHT 센서 종류: "DHT11" 또는 "DHT22"
DHT_TYPE = "DHT22"

# BCM GPIO 번호 기준
DHT_PIN = 4
LIGHT_PIN = 17

FAN_PIN = 27
PUMP_PIN = 22
BUZZER_PIN = 23

# 현재 팬/펌프 테스트 스크립트 기준으로 HIGH 신호에서 릴레이가 켜집니다.
# 장치가 반대로 동작하면 True/False를 다시 바꾸면 됩니다.
RELAY_ACTIVE_LOW = False

# 기본 부저 경보 기준 시간
ABNORMAL_DURATION_SECONDS = 60

DEFAULT_PLANT_CONFIG = {
    "plant_name": "바질",
    "min_temp": 20,
    "max_temp": 28,
    "min_humidity": 40,
    "max_humidity": 70,
    "light_required": "bright",
    "abnormal_duration_seconds": ABNORMAL_DURATION_SECONDS,
}

# MQTT settings
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")
MQTT_TOPIC_PREFIX = os.getenv("MQTT_TOPIC_PREFIX", "iot/plant-monitor")

# Email Notification
EMAIL_ENABLED = True

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

EMAIL_SENDER = "jyjjj0329@gachon.ac.kr"
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD", "")

EMAIL_RECEIVER = "jyjjj0329@gachon.ac.kr"

NOTIFICATION_COOLDOWN_SECONDS = 60
