from hardware import setup_hardware, read_sensor, set_fan, set_pump, set_buzzer
import time

setup_hardware()

print("센서 테스트 시작")
for i in range(5):
    data = read_sensor()
    print(data)
    time.sleep(2)

print("팬 테스트")
set_fan(True)
time.sleep(3)
set_fan(False)

print("펌프 테스트")
set_pump(True)
time.sleep(3)
set_pump(False)

print("부저 테스트")
set_buzzer(True)
time.sleep(1)
set_buzzer(False)

print("하드웨어 테스트 종료")