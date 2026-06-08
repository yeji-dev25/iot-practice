# config.py

# "mock"이면 가짜 센서값 사용
# "real"이면 실제 라즈베리파이 GPIO 사용
SENSOR_MODE = "mock"

# DHT 센서 종류: "DHT11" 또는 "DHT22"
DHT_TYPE = "DHT11"

# BCM GPIO 번호 기준
DHT_PIN = 4
LIGHT_PIN = 17

FAN_PIN = 27
PUMP_PIN = 22
BUZZER_PIN = 23

# 릴레이 모듈이 LOW 신호에서 켜지는 경우가 많음
# 장치가 반대로 동작하면 True/False 바꾸기
RELAY_ACTIVE_LOW = True

# 시연용: 원래는 3600초 = 1시간
# 오늘/내일 테스트는 30초 또는 60초 추천
ABNORMAL_DURATION_SECONDS = 30

DEFAULT_PLANT_CONFIG = {
    "plant_name": "바질",
    "min_temp": 20,
    "max_temp": 28,
    "min_humidity": 40,
    "max_humidity": 70,
    "light_required": "bright"
}