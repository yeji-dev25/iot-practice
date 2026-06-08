# Smart Plant Monitoring IoT Service

라즈베리파이를 기반으로 식물의 생장 환경을 모니터링하고, 기준값을 벗어났을 때 장치를 자동 또는 수동으로 제어할 수 있는 IoT 서비스입니다.

이 프로젝트는 다음 기능을 포함합니다.

- 온도, 습도, 조도 실시간 모니터링
- MQTT 기반 센서 데이터 Publish / Subscribe
- 팬, 펌프, 부저 자동 제어
- 웹 대시보드 기반 수동 제어
- 이메일 알림
- 최근 센서 이력 그래프
- 경보 기준 시간 웹 설정

## Project Structure

```text
sensor / actuator
    ↓
device_agent.py
    ↓ MQTT publish / subscribe
MQTT Broker
    ↓ MQTT publish / subscribe
app.py
    ↓
Web Dashboard
```

주요 데이터 흐름은 아래와 같습니다.

- 센서 데이터: `device_agent.py` -> MQTT Broker -> `app.py`
- 제어 명령: `app.py` -> MQTT Broker -> `device_agent.py`

## Files

- `app.py`: 웹 서비스 프로그램, 대시보드, 자동 제어 판단, MQTT 구독/발행
- `device_agent.py`: 라즈베리파이 디바이스 프로그램, 센서 읽기 및 장치 제어
- `hardware.py`: 센서 및 GPIO 장치 접근
- `config.py`: GPIO, MQTT, 기본 설정값, 이메일 설정
- `mqtt_service.py`: MQTT 공통 클라이언트 래퍼
- `mqtt_topics.py`: MQTT 토픽 정의
- `notifier.py`: 이메일 알림 전송
- `plant_config.json`: 현재 식물 설정 저장 파일
- `templates/index.html`: 웹 대시보드 UI

## Requirements

- Python 3.10+
- Raspberry Pi
- MQTT Broker
  - 권장: Mosquitto

파이썬 패키지 설치:

```bash
pip install -r requirements.txt
```

## Hardware Pins

현재 기본 핀 설정은 아래와 같습니다.

- `DHT_PIN = 4`
- `LIGHT_PIN = 17`
- `FAN_PIN = 27`
- `PUMP_PIN = 22`
- `BUZZER_PIN = 23`

`config.py`에서 필요에 따라 변경할 수 있습니다.

## Configuration

### Sensor Mode

테스트용 가짜 데이터:

```python
SENSOR_MODE = "mock"
```

실제 하드웨어 사용:

```python
SENSOR_MODE = "real"
```

### DHT Sensor Type

```python
DHT_TYPE = "DHT11"
```

또는

```python
DHT_TYPE = "DHT22"
```

### MQTT Settings

기본 MQTT 설정:

```python
MQTT_BROKER_HOST = "localhost"
MQTT_BROKER_PORT = 1883
MQTT_TOPIC_PREFIX = "iot/plant-monitor"
```

필요하면 `.env`에서 덮어쓸 수 있습니다.

```env
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883
MQTT_TOPIC_PREFIX=iot/plant-monitor
EMAIL_APP_PASSWORD=your_app_password
```

## How To Run

이 프로젝트는 아래 3개가 함께 실행되어야 합니다.

1. MQTT Broker
2. `device_agent.py`
3. `app.py`

### 1. Start MQTT Broker

예시: Mosquitto

```bash
mosquitto
```

### 2. Start Device Agent

```bash
python device_agent.py
```

역할:

- 센서 데이터 측정
- MQTT로 센서 데이터 Publish
- MQTT 제어 명령 Subscribe
- 팬 / 펌프 / 부저 제어

### 3. Start Web Service

```bash
python app.py
```

역할:

- MQTT로 센서 데이터 Subscribe
- 웹 대시보드 제공
- 자동 제어 로직 수행
- MQTT로 장치 제어 명령 Publish

### 4. Open Dashboard

로컬:

```text
http://localhost:5000
```

같은 네트워크의 다른 기기:

```text
http://<raspberry-pi-ip>:5000
```

## Dashboard Features

- 현재 온도 / 습도 / 조도 표시
- 최근 센서 추이 그래프
- 자동 / 수동 모드 전환
- 팬 / 펌프 / 부저 제어
- 식물 이름, 기준값, 경보 기준 시간 설정
- 비정상 상태 요약

## Auto Control Logic

자동 모드에서는 아래 규칙으로 동작합니다.

- 온도가 최대 기준보다 높으면 팬 ON
- 습도가 최소 기준보다 낮으면 펌프 ON
- 비정상 항목이 2개 이상이고 설정한 시간 이상 지속되면 부저 ON

비정상 항목은 다음을 기준으로 판단합니다.

- 온도
- 습도
- 조도

## MQTT Topics

기본 prefix: `iot/plant-monitor`

- 센서 데이터: `iot/plant-monitor/sensor`
- 장치 상태: `iot/plant-monitor/device-state`
- 제어 명령: `iot/plant-monitor/commands`
- 디바이스 상태: `iot/plant-monitor/status`

## Demo Flow

시연 시 추천 흐름:

1. 브로커 실행
2. `device_agent.py` 실행
3. `app.py` 실행
4. 웹 대시보드 접속
5. 센서값 표시 확인
6. 수동 제어 확인
7. 자동 제어 확인
8. 경보 동작 확인

## Troubleshooting

### 웹 화면은 뜨는데 센서값이 안 바뀌는 경우

- MQTT Broker가 실행 중인지 확인
- `device_agent.py`가 실행 중인지 확인
- MQTT 브로커 주소와 포트 확인

### 버튼은 눌리는데 장치가 안 움직이는 경우

- `device_agent.py`가 실행 중인지 확인
- GPIO 배선 확인
- 릴레이 모듈 전원 확인

### 센서값이 `None` 또는 오류로 나오는 경우

- 배선 확인
- 전원 확인
- `DHT_TYPE` 설정 확인
- `SENSOR_MODE` 설정 확인

### 릴레이가 반대로 동작하는 경우

`config.py`에서 아래 값을 조정합니다.

```python
RELAY_ACTIVE_LOW = True
```

필요하면 `False`로 바꿉니다.

## Notes

- `mock` 모드에서는 가짜 센서값으로 전체 흐름을 테스트할 수 있습니다.
- 실제 시연 전에는 `SENSOR_MODE = "real"`로 바꿔야 합니다.
- `plant_config.json`의 경보 기준 시간이 너무 길면 시연이 불편하므로 적절히 조정하는 것이 좋습니다.

## License

학습 및 과제 제출용 프로젝트입니다.
