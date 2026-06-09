import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hardware import read_sensor, setup_hardware

READ_COUNT = 5
READ_INTERVAL_SECONDS = 2


def main():
    setup_hardware(initialize_outputs=False)
    print("센서 전용 테스트 시작")

    for index in range(READ_COUNT):
        data = read_sensor()
        print(f"{index + 1}/{READ_COUNT} -> {data}")
        if index < READ_COUNT - 1:
            time.sleep(READ_INTERVAL_SECONDS)

    print("센서 전용 테스트 종료")


if __name__ == "__main__":
    main()
