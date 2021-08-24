import qwiic
from datetime import datetime
import PyNAU7802
import smbus2
import argparse
import json
import os
import time


class MuxBoard:

    def __init__(self, i2c):
        self.i2c = hex(int(i2c, 16))
        self.mux = qwiic.QwiicTCA9548A(self.i2c)
        self.ports = [0, 1, 2, 3, 4, 5, 6, 7]
        self.disable_port(self.ports)

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
        self.mux = mux
        self.port = port
        self.scale = PyNAU7802.NAU7802()
        self.zero_offset = float()
        self.cal_factor = float()

    def tare_scale(self):
        self.mux.enable_channels(self.port)
        self.scale.calculateZeroOffset()
        self.zero_offset = self.scale.getZeroOffset()
        cal = float(input("Mass in kg? "))
        self.scale.calculateCalibrationFactor(cal)
        self.cal_factor = self.scale.getCalibrationFactor()
        self.mux.disable_channels(self.port)

    def is_connected(self):
        bus = smbus2.SMBus(1)
        self.mux.enable_channels(self.port)
        try:
            if self.scale.begin(bus):
                return True
            else:
                return False
        finally:
            self.mux.disable_channels(self.port)

    def set_zero_offset(self):
        self.scale.setZeroOffset(self.zero_offset)

    def set_cal_factor(self):
        self.scale.setCalibrationFactor(self.cal_factor)

    def get_zero_offset(self):
        return self.zero_offset

    def get_cal_factor(self):
        return self.cal_factor

    def get_port(self):
        return self.port

    def get_weight(self):
        self.mux.enable_channels(self.port)
        self.set_zero_offset()
        self.set_cal_factor()
        five_weights = [self.scale.getWeight() for i in range(5)]
        average_weight = round((sum(five_weights) / len(five_weights)), 3)
        self.mux.disable_channels(self.port)
        return average_weight

    def write_calibration(self, file):
        scale_cal = {self.port: (self.get_zero_offset(), self.get_cal_factor())}
        try:
            with open(file, "r+") as cal_file:
                cal_dict = json.load(cal_file)
                if self.mux in cal_dict.keys():
                    cal_dict[self.mux].update(scale_cal)
                else:
                    cal_dict.setdefault(self.mux, scale_cal)
                json.dump(cal_dict, cal_file, indent=4, sort_keys=True)
        except IOError:
            with open(file, "w+") as cal_file:
                cal_dict = {self.mux: scale_cal}
                json.dump(cal_dict, cal_file, indent=4, sort_keys=True)


class Experiment:
    def __init__(self, treatments):
        with open(treatments, "r") as f:
            self.treatment_dict = json.load(f)
        self.mux_dict = dict()

        for i in self.treatment_dict["valves"].keys():
            self.mux_dict.setdefault(i, MuxBoard(self.treatment_dict["valves"][i]["mux_address"]))

    def calibrate_scales(self):

        for valve, mux in zip(self.treatment_dict["valves"].keys(), self.mux_dict.keys()):
            scales_dict = dict()
            scales_dict.setdefault(self.treatment_dict["valves"][valve],
                                   Scale(mux, valve))
            for scale in scales_dict.keys():
                if scales_dict[scale].is_connected():
                    print("tare scale on port {0}".format(scales_dict[scale].get_port()))
                    scales_dict[scale].tare_scale()
                    scales_dict[scale].write_calibration(os.path.join(self.treatment_dict["output_dir"],
                                                                      self.treatment_dict["cal_file"]))


def main():
    """
    Main method.
    :return: None
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--treatment", help="path to treatments json file")
    args = parser.parse_args()
    treatment_file = args.treatment
    print("{0}:########Starting Qwiic scales#########\n".format(datetime.now()))
    my_experiment = Experiment(treatment_file)
    my_experiment.calibrate_scales()
    print("finished")


if __name__ == "__main__":
    main()

