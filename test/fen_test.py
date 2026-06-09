import RPi.GPIO as GPIO
import time

FAN_RELAY_PIN = 27   # GPIO27 = 물리핀 13번

GPIO.setmode(GPIO.BCM)
GPIO.setup(FAN_RELAY_PIN, GPIO.OUT)

try:
    print("팬 ON")
    GPIO.output(FAN_RELAY_PIN, GPIO.HIGH)   # 릴레이가 안 켜지면 HIGH로 바꾸기
    time.sleep(5)

    print("팬 OFF")
    GPIO.output(FAN_RELAY_PIN, GPIO.LOW)  # 위에서 HIGH로 바꿨으면 여기는 LOW
    time.sleep(1)

finally:
    GPIO.cleanup()