from w1thermsensor import W1ThermSensor
import board
import busio
import time
from datetime import datetime
i2c = busio.I2C(board.SCL, board.SDA)
import RPi.GPIO as GPIO
import json
import sync_data


# Set GPIO pins to use BCM pin numbers
GPIO.setmode(GPIO.BCM)

# Set digital pin 24 to an input
GPIO.setup(24, GPIO.IN)


class Solenoid:
    def __init__(self, channel):
        self.channel = channel
        GPIO.setup(channel, GPIO.OUT)
        GPIO.setup(21, GPIO.OUT)

    def open_valve(self):

        GPIO.output(21, GPIO.HIGH)
        GPIO.output(self.channel, GPIO.HIGH)

    def close_valve(self):
        GPIO.output(self.channel, GPIO.LOW)
        GPIO.output(21, GPIO.LOW)

    def water(self, amount, rate=0.52575):
        open_time = float(amount) / float(rate)
        print("watering for {0} minutes".format(round(open_time/60, ndigits=2)))
        self.open_valve()
        time.sleep(open_time)
        self.close_valve()


class ds18b20:
    def __init__(self):
        self.ds18b20 = W1ThermSensor()
        self.log = dict()

    def get_temperature(self):
        return self.ds18b20.get_temperature()

    def log_temperature(self):
        self.log.setdefault(datetime.now().isoformat(), self.get_temperature())

    def get_temp_record(self):
        return self.log


class Experiment:
    def __init__(self, treatments):
        with open(treatments, "r") as f:
            treatment_dict = json.load(f)


def main():
    t1 = ds18b20()
    t1.log_temperature()
    print(t1.get_temp_record())
    s1 = Solenoid(13)
    s1.water(amount=100)
    #s6 = Solenoid(21)
    #s6.water(100)


if __name__ == "__main__":
    main()



