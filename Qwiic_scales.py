import qwiic
from datetime import datetime
import PyNAU7802
import smbus2
import argparse
import json
import os
import time


def enable_port(mux, ports):
    """
    Enables ports on QwiicTCA9548A multiplexer
    :param mux: QwiicTCA9548A multiplexer instance
    :param ports: Multiplexer port(s) to enable.
    :return: None
    """
    mux.enable_channels(ports)


def disable_port(mux, ports):
    """
        disables ports on QwiicTCA9548A multiplexer
        :param mux: QwiicTCA9548A multiplexer instance
        :param ports: Multiplexer port(s) to disable.
        :return: None
        """
    time.sleep(1)
    mux.disable_channels(ports)


def initialize_mux():
    """
    Creates a QwiicTCA9548A multiplexer instance
    :return: QwiicTCA9548A multiplexer instance

    """
    my_mux = qwiic.QwiicTCA9548A()
    ports = [0, 1, 2, 3, 4, 5, 6, 7]
    # disable all channels
    disable_port(my_mux, ports)

return my_mux


def create_bus():
    """
    Creates a  SMBus instance
    :return: SMBus instance
    """
    bus = smbus2.SMBus(1)
    return bus


def initialize_scales(ports):
    """
    Connects to scales on multiplexer port(s).
    :param ports: Multiplexer port(s) connected to NAU7802 scale amplifier boards
    :return: Dictionary with port as the key and a scale instance as the value
    """
    scales = dict()
    my_mux = initialize_mux()
    bus = create_bus()
    for port in ports:
        enable_port(my_mux, port)
        scales.setdefault(str(port), PyNAU7802.NAU7802())
        if scales[str(port)].begin(bus):
            print("Connected to scale {0} \n".format(port))
        else:
            print("Can't find scale on port {0}, skipping...\n".format(port))
        disable_port(my_mux, port)
    return scales


def tare_scales(mux, scales, output):
    """
    Sets the Zero offset and calibration factor for all scales connected to the multiplexer.
    :param mux: QwiicTCA9548A multiplexer instance
    :param scales: Dictionary with scale instances returned by initialize_scales()
    :param output: Path to output directory. Will be created if does not exist
    :return: Dictionary with port as key and list of [zero offset, calibration factor] as value.
    """
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
    with open(os.path.join(output, "cal_file.json"), "w+") as cal_file:
        json.dump(cal_dict, cal_file, indent=4, sort_keys=True)
    input("Press [Enter] to complete calibration")
    print("{0}: New calibration saved {1}".format(datetime.now(),
                                                  os.path.join(output, "cal_file.json")))

    return cal_dict


def set_calibration(mux, scales, cal, port, output):
    """
    Set scale calibration factor and zero offset using stored values.
    :param mux: QwiicTCA9548A multiplexer instance
    :param scales: Dictionary with scale instances returned by initialize_scales()
    :param cal: Dictionary with calibration information returned by tare_scales()
    :param port: Multiplexer port connected to NAU7802 scale amplifier board
    :param output: Path to output directory
    :return: None
    """
    enable_port(mux, int(port))
    try:
        zero_offset = cal[port][0]
        cal_factor = cal[port][1]

        if cal_factor == 0:
            print("adjusting calibration factor to 1")
            cal_factor = 1  # reset cal_factor if 0
        scales[port].setZeroOffset(zero_offset)
        scales[port].setCalibrationFactor(cal_factor)
        print("{0}: Calibration for scale on port {1} set. \n"
              "Calibration factor: {2} \n"
              "Zero Offset: {3}".format(datetime.now(), port, cal_factor, zero_offset))
        disable_port(mux, int(port))

    except KeyError:
        print("No calibration found for scale at port {0}, "
              "trying to set a new calibration".format(port))
        tare_scales(mux, scales, output)
        disable_port(mux, int(port))


def get_manual_weights(mux, scales, cal, output):
    """
    Get weights from scales in interactive mode.
    :param mux: QwiicTCA9548A multiplexer instance
    :param scales: Dictionary with scale instances returned by initialize_scales()
    :param cal: Dictionary with calibration information returned by tare_scales()
    :param output: Path to output directory
    :return: None
    """
    for i in scales.keys():
        set_calibration(mux, scales, cal, i, output)
        enable_port(mux, int(i))
        input("Press [Enter] to measure a mass. ")
        print("Mass is {0:0.3f} kg".format(scales[i].getWeight()))
        disable_port(mux, int(i))


def write_weight_json(weights, weight_data, output):
    """
    Write weight data to JSON file.
    :param weights: Dictionary with timestamp as key and  dictionary of weights as value
    :param weight_data: JSON file containing previous weights logged.
    :param output: Path to output directory
    :return: None
    """
    if os.path.exists(os.path.join(output, weight_data)):
        print("found existing data file, appending new data")
        with open(os.path.join(output, weight_data), "r") as infile:
            my_weights = json.load(infile)
            my_weights.update(weights)

    else:
        my_weights = weights

    with open(os.path.join(output, weight_data), "w") as outfile:
        json.dump(my_weights, outfile, indent=4, sort_keys=True)


def get_weights(mux, scales, cal, output, weight_data):
    """

    :param mux: QwiicTCA9548A multiplexer instance
    :param scales: Dictionary with scale instances returned by initialize_scales()
    :param cal: Dictionary with calibration information returned by tare_scales()
    :param output: Path to output directory
    :param weight_data: JSON file containing previous weights logged.
    :return: Dictionary with start timestamp as key and dictionary of {timestamp: weight} as value.
    """
    weight_dict = dict()
    start_time = datetime.now().isoformat()
    for i in scales.keys():
        print(i)
        set_calibration(mux, scales, cal, i, output)
        enable_port(mux, int(i))
        # get 4 weight readings and average them
        weight = [scales[i].getWeight() for j in range(4)]
        weight_avg = sum(weight) / len(weight)
        # round weight to 2 decimals and add timestamp
        my_weight = (round(weight_avg, 2), datetime.now().isoformat())
        weight_dict.setdefault(i, my_weight)
        disable_port(mux, int(i))

    weights = {start_time: weight_dict}
    write_weight_json(weights, weight_data, output)
    return weights


def read_cal_file(file_path):
    """
    Reads calibration data from JSON file.
    :param file_path: Path to JSON file with calibration data
    :return: Dictionary with port ID as key and list of [zero offset, calibration factor] as value.
    """
    with open(file_path, "r") as cal_file:
        cal_dict = json.load(cal_file)
    return cal_dict


def main():
    """
    Main method.
    :return: None
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--ports",
                        help="list of scale ports on mux (0-7_ separated by commas.")
    parser.add_argument("-c", "--cal", help="path to calibration file", default=None)
    parser.add_argument("-o", "--output", help="path to output directory", default=".")
    parser.add_argument("-w", "--weight_data", help="weight data json file", default="weight_data.json")
    parser.add_argument("-m", "--manual", help="get manual weight readings", default=False, type=bool)
    parser.add_argument("-nc", "--new_cal", help="recalibrate the scales", default=False, type=bool)
    args = parser.parse_args()
    ports = [int(i) for i in args.ports.strip().split(",")]
    cal_file = args.cal
    output = args.output
    weight_data = args.weight_data
    manual = args.manual
    new_cal = args.new_cal
    print("{0}:########Starting Qwiic scales#########\n".format(datetime.now()))

    my_mux = initialize_mux()
    scales = initialize_scales(ports)
    if new_cal is True:
        print("{0}: Setting new scale calibration")
        tare_scales(my_mux, scales, output)
        exit(0)
    if cal_file is not None:
        print("{0} reading calibration".format(datetime.now()))
        cal = read_cal_file(cal_file)
        print("read calibration...")
    else:
        cal = tare_scales(my_mux, scales, output)

    if manual is True:
        get_manual_weights(my_mux, scales, cal, output)
    else:
        print("{0}: Reading weights...".format(datetime.now()))
        get_weights(my_mux, scales, cal, output, weight_data)


if __name__ == "__main__":
    main()