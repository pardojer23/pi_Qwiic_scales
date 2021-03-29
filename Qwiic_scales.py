import qwiic
from datetime import datetime
import PyNAU7802
import smbus2
import argparse
import json
import os


def enable_port(mux, ports):
    mux.enable_channels(ports)


def disable_port(mux, ports):
    mux.disable_channels(ports)


def initialize_mux():
    my_mux = qwiic.QwiicTCA9548A()
    ports = [0, 1, 2, 3, 4, 5, 6, 7]
    # disable all channels
    disable_port(my_mux, ports)
    return my_mux


def create_bus():
    bus = smbus2.SMBus(1)
    return bus


def initialize_scales(ports):
    scales = dict()
    my_mux = initialize_mux()
    bus = create_bus()
    for port in ports:
        enable_port(my_mux, port)
        scales.setdefault(str(port), PyNAU7802.NAU7802())
        if scales[str(port)].begin(bus):
            print("Connected to scale {0} \n".format(port))
        else:
            print("Can't find scale on port {0}, exiting ...\n".format(port))
        disable_port(my_mux, port)
    return scales


def tare_scales(mux, scales, output):
    cal_dict = dict()
    for i in scales.keys():

        enable_port(mux, int(i))
        print("Calculating the zero offset for scale on port {0}...".format(i))
        scales[i].calculateZeroOffset()
        zero_offset = scales[i].getZeroOffset()
        print("The zero offset for scale at port {0} is:"
              " {1}\n".format(i, zero_offset))

        print("Put a known mass on the scale at port {0}.".format(i))
        cal = float(input("Mass in kg? "))

        # Calculate the calibration factor
        print("Calculating the calibration factor...")
        scales[i].calculateCalibrationFactor(cal)
        cal_factor = scales[i].getCalibrationFactor()
        print("The calibration factor for scale at port {0} is:"
              " {1:0.3f}\n".format(i, cal_factor))
        cal_dict.setdefault(i, [zero_offset, cal_factor])
        disable_port(mux, int(i))
    if os.path.isdir(output):
        pass
    else:
        os.mkdir(output)
    with open(os.path.join(output,"cal_file.json"), "w+") as cal_file:
        json.dump(cal_dict, cal_file, indent=4, sort_keys=True)
    return cal_dict


def get_manual_weights(mux, scales, cal, output):
    for i in scales.keys():
        enable_port(mux, int(i))
        try:
            scales[i].setZeroOffset(cal[i][0])
            scales[i].setCalibrationFactor(cal[i][1])
        except KeyError:
            print("No calibration found for scale at port {0}, "
                  "trying to set a new calibration".format(i))
            tare_scales(mux, scales, output)

        input("Press [Enter] to measure a mass. ")
        print("Mass is {0:0.3f} kg".format(scales[i].getWeight()))
        disable_port(mux, int(i))


def get_weights(mux, scales, cal, output, weight_data):
    weight_dict = dict()
    start_time = datetime.now().isoformat()
    for i in scales.keys():
        enable_port(mux, int(i))
        try:
            scales[i].setZeroOffset(cal[i][0])
            scales[i].setCalibrationFactor(cal[i][1])
        except KeyError:
            print("No calibration found for scale at port {0}, "
                  "trying to set a new calibration".format(i))
            tare_scales(mux, scales, output)

        weight = (scales[i].getWeight(), datetime.now().isoformat())
        weight_dict.setdefault(scales[i], weight)
        disable_port(mux, int(i))

    with open(os.path.join(output, weight_data), "w+") as outfile:
        weights = {"start_time": start_time,
                   "weights": weight_dict}
        print(weights)
        json.dump(weights, outfile, indent=4, sort_keys=True)




def read_cal_file(file_path):
    with open(file_path, "r") as cal_file:
        cal_dict = json.load(cal_file)
    return cal_dict


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--ports",
                        help="list of scale ports on mux (0-7_ separated by commas.")
    parser.add_argument("-c", "--cal", help="path to calibration file", default=None)
    parser.add_argument("-o", "--output", help="path to output directory", default=".")
    parser.add_argument("-w", "--weight_data", help="weight data json file", default="weight_data.json")
    args = parser.parse_args()
    ports = [int(i) for i in args.ports.strip().split(",")]
    cal_file = args.cal
    output = args.output
    weight_data = args.weight_data

    my_mux = initialize_mux()
    scales = initialize_scales(ports)
    if cal_file is not None:
        cal = read_cal_file(cal_file)
    else:
        cal = tare_scales(my_mux, scales, output)

    get_weights(my_mux, scales, cal, output, weight_data)


if __name__ == "__main__":
    main()