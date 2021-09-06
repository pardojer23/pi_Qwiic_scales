from w1thermsensor import W1ThermSensor
import board
import busio
import time
from datetime import datetime
i2c = busio.I2C(board.SCL, board.SDA)
import RPi.GPIO as GPIO
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import argparse



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

    def water_time(self, amount, rate=0.6666):
        open_time = float(amount) / float(rate)
        return open_time

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
            self.treatment_dict = json.load(f)
        self.solenoid_dict = {}
        for valve in self.treatment_dict["valves"].keys():

            self.solenoid_dict.setdefault("s" + str(self.treatment_dict["valves"][valve]["valve_number"]),
                                          Solenoid(valve["valve_pin"]))

    def read_gs_data(self, spreadsheet, sheet_name):
        scope = ['https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive']
        credentials = ServiceAccountCredentials.from_json_keyfile_name(
            self.treatment_dict["gdrive_credential"], scope)
        gc = gspread.authorize(credentials)
        sheet = gc.open(spreadsheet).worksheet(sheet_name)
        gs_df = pd.DataFrame(sheet.get_all_records())
        return gs_df

    def get_water_amount(self):
        water_log = self.read_gs_data(self.treatment_dict["spreadsheet"], "irrigation_log")
        water_log["timestamp"] = pd.to_datetime(water_log["timestamp"])
        weight_df = self.read_gs_data(self.treatment_dict["spreadsheet"],
                                      self.treatment_dict["sheet_name"])

    def write_temp_data(self, spreadsheet, sheet_name):
        temp_guage = ds18b20()
        temp = temp_guage.get_temperature()
        current_time = datetime.now().isoformat()
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
        credentials = ServiceAccountCredentials.from_json_keyfile_name(
                self.treatment_dict["gdrive_credential"], scope)
        gc = gspread.authorize(credentials)
        sheet = gc.open(spreadsheet)
        values = [[current_time, temp]]
        sheet.values_append(sheet_name,
                            {'valueInputOption': "USER_ENTERED"},
                            {'values': values})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--treatment", help="path to treatments json file")
    args= parser.parse_args()
    treatment_file = args.treatment
    my_experiment = Experiment(treatment_file)
    my_experiment.write_temp_data(spreadsheet=my_experiment.treatment_dict["spreadsheet"],
                                  sheet_name="temperature_log")
if __name__ == "__main__":
    main()



