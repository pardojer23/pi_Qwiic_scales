import qwiic
from datetime import datetime
import PyNAU7802
import smbus2
import argparse
import json
import os
import gspread
import gspread_dataframe
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd



import time


class MuxBoard:

    def __init__(self, i2c):
        self.i2c = int(i2c, 16)
        self.mux = qwiic.QwiicTCA9548A(address=self.i2c)
        self.ports = [0, 1, 2, 3, 4, 5, 6, 7]
        self.disable_port(self.ports)
        if self.mux.is_connected():
            print("Successfully connected to QwiicTCA9548A at {0}".format(hex(self.i2c)))
        else:
            print("Connection Failed for QwiicTCA9548A at {0}!".format(hex(self.i2c)))

    def enable_port(self, ports):
        """
            Enables ports on QwiicTCA9548A multiplexer
            :param ports: Multiplexer port(s) to enable.
            :return: None
            """
        self.mux.enable_channels(ports)

    def disable_port(self, ports):
        """
                disables ports on QwiicTCA9548A multiplexer
                :param ports: Multiplexer port(s) to disable.
                :return: None
        """
        self.mux.disable_channels(ports)


class Scale:

    def __init__(self, mux, port):
        self.mux_board = mux
        self.port = int(port)
        self.scale = PyNAU7802.NAU7802()
        self.zero_offset = float()
        self.cal_factor = float()

    def tare_scale(self):
        self.mux_board.mux.enable_channels(self.port)
        self.scale.calculateZeroOffset()
        self.zero_offset = self.scale.getZeroOffset()
        cal = float(input("Enter Mass in kg"))
        self.scale.calculateCalibrationFactor(cal)
        self.cal_factor = self.scale.getCalibrationFactor()
        self.mux_board.mux.disable_channels(self.port)

    def is_connected(self):
        bus = smbus2.SMBus(1)
        self.mux_board.mux.enable_channels(self.port)
        try:
            if self.scale.begin(bus):
                return True
            else:
                return False
        finally:
            self.mux_board.mux.disable_channels(self.port)

    def set_zero_offset(self, zero_offset):
        self.scale.setZeroOffset(zero_offset)

    def set_cal_factor(self, cal_factor):
        self.scale.setCalibrationFactor(cal_factor)

    def get_zero_offset(self):
        return self.zero_offset

    def get_cal_factor(self):
        return self.cal_factor

    def get_port(self):
        return self.port

    def get_weight(self):
        self.mux_board.mux.enable_channels(self.port)
        five_weights = [self.scale.getWeight() for i in range(5)]
        average_weight = round((sum(five_weights) / len(five_weights)), 3)
        self.mux_board.mux.disable_channels(self.port)
        return average_weight

    def write_calibration(self, file):
        scale_cal = {str(self.port): (self.get_zero_offset(), self.get_cal_factor())}
        mux_id = hex(self.mux_board.i2c)
        try:
            with open(file, "r+") as cal_file:
                cal_dict = json.load(cal_file)
                if mux_id in cal_dict.keys():
                    cal_dict[mux_id].update(scale_cal)
                else:
                    cal_dict.setdefault(mux_id, scale_cal)
                cal_file.seek(0)
                cal_file.write(json.dumps(cal_dict, indent=4, sort_keys=True))
                cal_file.truncate()

        except IOError:
            with open(file, "w+") as cal_file:
                cal_dict = {mux_id: scale_cal}
                json.dump(cal_dict, cal_file, indent=4, sort_keys=True)


class Experiment:
    def __init__(self, treatments):
        with open(treatments, "r") as f:
            self.treatment_dict = json.load(f)
        self.mux_dict = dict()

        for i in self.treatment_dict["valves"].keys():
            self.mux_dict.setdefault(i, MuxBoard(self.treatment_dict["valves"][i]["mux_address"]))

    def get_scales_dict(self, scales):
        scales_dict = dict()
        if scales.lower() == "all":
            for valve, mux in zip(self.treatment_dict["valves"].keys(), self.mux_dict.keys()):
                scales_dict.setdefault(mux, {})
                for port in self.treatment_dict["valves"][valve]["scales"]:
                    scales_dict[mux].setdefault(port, Scale(self.mux_dict[mux], port))
        else:

            scale_list = scales.strip().split(",")
            for pair in scale_list:
                split_pair = pair.strip().split("-")
                mux_address = split_pair[0]
                scale = split_pair[1]
                if mux_address in scales_dict.keys():
                    scales_dict[mux_address].setdefault(scale, Scale(MuxBoard(mux_address), scale))
                else:
                    scales_dict.setdefault(mux_address, {scale: Scale(MuxBoard(mux_address), scale)})
        return scales_dict

    def calibrate_scales(self, scales):
        scales_dict = self.get_scales_dict(scales)
        print(scales_dict)
        for mux in scales_dict.keys():
            for scale in scales_dict[mux].keys():
                if scales_dict[mux][scale].is_connected():
                    print("tare scale on multiplexer {0} port {1}".format(mux, scales_dict[mux][scale].get_port()))
                    scales_dict[mux][scale].tare_scale()
                    scales_dict[mux][scale].write_calibration(os.path.join(self.treatment_dict["output_dir"],
                                                                           self.treatment_dict["cal_file"]))

    def read_weights(self, scales):
        cal_file_path = os.path.join(self.treatment_dict["output_dir"], self.treatment_dict["cal_file"])
        with open(cal_file_path, "r") as cal_file:
            cal_dict = json.load(cal_file)
        scales_dict = self.get_scales_dict(scales)
        print(scales_dict)
        mux_list = []
        scale_list = []
        weight_list = []
        for mux in scales_dict.keys():
            for scale in scales_dict[mux].keys():
                if scales_dict[mux][scale].is_connected():
                    print("Reading weight from scale on multiplexer {0} port {1}".format(mux, scales_dict[mux][scale].get_port()))
                    zero_offset = cal_dict[mux][scale][0]
                    cal_factor = cal_dict[mux][scale][1]
                    scales_dict[mux][scale].set_zero_offset(zero_offset)
                    scales_dict[mux][scale].set_cal_factor(cal_factor)
                    weight_list.append(scales_dict[mux][scale].get_weight())
                    mux_list.append(mux)
                    scale_list.append(scale)
        current_time = datetime.now().isoformat()
        timestamp = [current_time for i in range(len(scale_list))]
        weight_df = pd.DataFrame({"Timestamp": timestamp,
                                  "Multiplexer": mux_list,
                                  "Scale": scale_list,
                                  "Weight": weight_list})
        return weight_df

    def write_weights(self, spreadsheet, sheet_name, scales):
        weight_df = self.read_weights(scales)
        scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
        credentials = ServiceAccountCredentials.from_json_keyfile_name(
                        self.treatment_dict["gdrive_credential"], scope)
        gc = gspread.authorize(credentials)
        sheet = gc.open(spreadsheet)
        values = weight_df.values.tolist()
        sheet.values_append(sheet_name,
                            {'valueInputOption': "USER_ENTERED"},
                            {'values': values})



def main():
    """
    Main method.
    :return: None
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--treatment", help="path to treatments json file")
    parser.add_argument("-s", "--scales", help="scales to read weights from (multiplexer address - scale) \n"
                                                  "eg. 0x70-0,0x71-2 set to all to read all scales", default="all")
    parser.add_argument("-c", "--calibrate", help="scales to calibrate (multiplexer address - scale) \n"
                                                  "eg. 0x70-0,0x71-2 set to all to calibrate all scales", default=None)
    args = parser.parse_args()
    treatment_file = args.treatment
    calibrate = args.calibrate
    scales = str(args.scales)
    print("{0}:########Starting Qwiic scales#########\n".format(datetime.now()))
    my_experiment = Experiment(treatment_file)
    if calibrate is not None:
        my_experiment.calibrate_scales(calibrate)
    else:
        my_experiment.write_weights(spreadsheet=my_experiment.treatment_dict["spreadsheet"],
                                    sheet_name=my_experiment.treatment_dict["sheet_name"],
                                    scales=scales)

    print("finished")


if __name__ == "__main__":
    main()

