from w1thermsensor import W1ThermSensor
import board
import busio
import time
i2c = busio.I2C(board.SCL, board.SDA)
import RPi.GPIO as GPIO
#Assign channels to variables to keep track of them
s1 = 13
s2 = 16
s3 = 19
s4 = 20
s5 = 26
s6 = 21

# Set GPIO pins to use BCM pin numbers
GPIO.setmode(GPIO.BCM)

# Set digital pin 24 to an input
GPIO.setup(24, GPIO.IN)
# Set solenoid driver pins to outputs:
GPIO.setup(s1, GPIO.OUT)  # set Solenoid 1 output
GPIO.setup(s2, GPIO.OUT)  # set Solenoid 2 output
GPIO.setup(s3, GPIO.OUT)  # set Solenoid 3 output
GPIO.setup(s4, GPIO.OUT)  # set Solenoid 4 output
GPIO.setup(s5, GPIO.OUT)  # set Solenoid 5 output
GPIO.setup(s6, GPIO.OUT)  # set Solenoid 6 output

#Test Solenoids by turning each on for a half second
GPIO.output(s1, GPIO.HIGH) #turn solenoid 1 on
time.sleep(0.5) #Wait for a half second
GPIO.output(s1, GPIO.LOW) #turn solenoid 1 off
time.sleep(0.5)