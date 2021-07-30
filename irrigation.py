#from w1thermsensor import W1ThermSensor
import board
import busio
import time
i2c = busio.I2C(board.SCL, board.SDA)
import RPi.GPIO as GPIO
import sync_data


# Set GPIO pins to use BCM pin numbers
GPIO.setmode(GPIO.BCM)

# Set digital pin 24 to an input
GPIO.setup(24, GPIO.IN)


class Solenoid:
    def __init__(self, channel):
        self.channel = channel
        GPIO.setup(channel, GPIO.OUT)

    def open_valve(self):
        GPIO.output(self.channel, GPIO.HIGH)

    def close_valve(self):
        GPIO.output(self.channel, GPIO.LOW)

    def water(self, amount, rate=2.103):
        open_time = float(amount) / float(rate)
        print("watering for {0} minutes".format(round(open_time/60, ndigits=2)))
        self.open_valve()
        time.sleep(open_time)
        self.close_valve()

def main():
    s1 = Solenoid(13)
    s1.water(amount=10)


if __name__ == "__main__":
    main()



