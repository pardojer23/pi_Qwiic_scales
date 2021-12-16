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
from statistics import mean
import multiprocessing

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

    def water_time(self, amount, rate=0.525):
        # rate is ml/ second
        open_time = float(amount) / float(rate)
        return open_time

    def water(self, open_time):
        self.open_valve()
        time.sleep(open_time)
        self.close_valve()
        current_time = datetime.now().isoformat()
        return current_time

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
                                          Solenoid(self.treatment_dict["valves"][valve]["valve_pin"]))

    def read_gs_data(self, spreadsheet, sheet_name):
        scope = ['https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive']
        credentials = ServiceAccountCredentials.from_json_keyfile_name(
            self.treatment_dict["gdrive_credential"], scope)
        gc = gspread.authorize(credentials)
        sheet = gc.open(spreadsheet).worksheet(sheet_name)
        gs_df = pd.DataFrame(sheet.get_all_records())
        return gs_df

    def get_water_lost(self):
        water_log = self.read_gs_data(self.treatment_dict["spreadsheet"], "irrigation_log")
        water_log["timestamp"] = pd.to_datetime(water_log["timestamp"])
        weight_df = self.read_gs_data(self.treatment_dict["spreadsheet"],
                                      self.treatment_dict["sheet_name"])
        weight_df["datetime"] = [pd.to_datetime(i) for i in weight_df["Timestamp"]]
        if len(water_log.index) > 0:
            last_watering = water_log.loc[max(water_log.index), "timestamp"]
            recent_weight = weight_df.loc[weight_df["datetime"] > last_watering]
        else:
            recent_weight = weight_df
        water_lost = dict()
        for group in recent_weight.groupby(["Multiplexer", "Scale"]):
            prev_weight = group[1].loc[min(group[1].index), "Weight"]
            cur_weight = group[1].loc[max(group[1].index), "Weight"]
            diff = cur_weight - prev_weight
            water_lost.setdefault(group[0][0], []).append(diff)
        return water_lost

    def get_water_amount(self):
        water_lost = self.get_water_lost()
        water_amount = dict()
        for valve in water_lost.keys():
            avg_loss = mean(water_lost[valve])
            amount = self.treatment_dict["valves"][valve]["amount"]*avg_loss
            water_amount.setdefault(valve, amount)
        return water_amount

    def water_pots(self, spreadsheet):
        sm = Solenoid(21)
        solenoid_dict = dict()
        water_amount = self.get_water_amount()
        sm.open_valve()
        for valve in water_amount:
            solenoid_dict.setdefault(valve, Solenoid(self.treatment_dict["valves"][valve]["valve_pin"]))

        manager = multiprocessing.Manager()
        return_dict = manager.dict()
        jobs = []
        for valve in solenoid_dict.keys():
            p = multiprocessing.Process(target=solenoid_dict[valve].water,
                                        args=(solenoid_dict[valve].water_time(
                                                    amount=water_amount[valve]), return_dict))
            jobs.append(p)
            p.start()
        for process in jobs:
            process.join()
        sm.close_valve()
        self.write_water_data(spreadsheet, water_amount)

    def get_water_info(self, water_amount):
        water_amount = water_amount
        timestamp = [datetime.now().isoformat() for i in range(len(water_amount.keys()))]
        valve = [i for i in water_amount.keys()]
        target_amount = [water_amount[i] for i in water_amount.keys()]
        water_df = pd.DataFrame({"timestamp": timestamp,
                                 "valve": valve,
                                 "target_amount": target_amount})
        return water_df

    def write_water_data(self, spreadsheet, water_amount):
        water_df = self.get_water_info(water_amount=water_amount)
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
        credentials = ServiceAccountCredentials.from_json_keyfile_name(
            self.treatment_dict["gdrive_credential"], scope)
        gc = gspread.authorize(credentials)
        sheet = gc.open(spreadsheet)
        values = water_df.values.tolist()
        sheet.values_append("irrigation_log",
                            {'valueInputOption': "USER_ENTERED"},
                            {'values': values})

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
    parser.add_argument("-w", "--water", help="Water the pots if True", default="false")
    args= parser.parse_args()
    treatment_file = args.treatment
    water = args.water
    if water.lower().isin(["true", "t", "1", "on"]):
        water = True
    else:
        water = False
    my_experiment = Experiment(treatment_file)
    my_experiment.write_temp_data(spreadsheet=my_experiment.treatment_dict["spreadsheet"],
                                  sheet_name="temperature_log")
    if water is True:
        my_experiment.water_pots(spreadsheet=my_experiment.treatment_dict["spreadsheet"])
if __name__ == "__main__":
    main()



