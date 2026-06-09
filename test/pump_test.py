import RPi.GPIO as GPIO
import time

RELAY_PIN = 22

GPIO.setmode(GPIO.BCM)
GPIO.setup(RELAY_PIN, GPIO.OUT)

try:
    print("펌프 ON")
    GPIO.output(RELAY_PIN, GPIO.HIGH)   # 안 켜지면 HIGH로 바꾸기
    time.sleep(3)

    print("펌프 OFF")
    GPIO.output(RELAY_PIN, GPIO.LOW)  # 안 꺼지면 LOW로 바꾸기
    time.sleep(1)

finally:
    GPIO.cleanup()