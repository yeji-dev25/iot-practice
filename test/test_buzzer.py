import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import RPi.GPIO as GPIO

from config import BUZZER_PIN

BUZZER_ON_SECONDS = 1


def main():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(BUZZER_PIN, GPIO.OUT, initial=GPIO.LOW)

    try:
        print(f"부저 테스트 시작(GPIO{BUZZER_PIN})")
        GPIO.output(BUZZER_PIN, GPIO.HIGH)
        time.sleep(BUZZER_ON_SECONDS)
        GPIO.output(BUZZER_PIN, GPIO.LOW)
        print("부저 테스트 종료")
    finally:
        GPIO.cleanup(BUZZER_PIN)


if __name__ == "__main__":
    main()
