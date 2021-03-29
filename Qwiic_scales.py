import qwiic
import time
import PyNAU7802
import smbus2
import argparse


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
        scales.setdefault(port, PyNAU7802.NAU7802())
        if scales[port].begin(bus):
            print("Connected to scale {0} \n".format(port))
        else:
            print("Can't find scale on port {0}, exiting ...\n".format(port))
        disable_port(my_mux, port)
    return scales


def tare_scales(mux, scales):
    for i in scales.keys():
        print(i)
        enable_port(mux, i)
        print("Calculating the zero offset for scale on port {0}...").format(int(i))
        scales[i].calculateZeroOffset()
        print("The zero offset for scale at port {0} is:"
              " {1}\n".format(int(i), scales[i].getZeroOffset()))
        print("Put a known mass on the scale at port {0}.".format(int(i)))
        cal = float(input("Mass in kg? "))

        # Calculate the calibration factor
        print("Calculating the calibration factor...")
        scales[i].calculateCalibrationFactor(cal)
        print("The calibration factor for scale at port {0} is:"
              " {0:0.3f}\n".format(i, scales[i].getCalibrationFactor()))
        disable_port(mux, i)


def get_weights(mux, scales):
    for i in scales.keys():
        enable_port(mux, i)
        print("Mass is {0:0.3f} kg".format(scales[i].getWeight()))
        disable_port(mux, i)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--ports",
                        help="list of scale ports on mux (0-7_ separated by commas.")
    args = parser.parse_args()
    ports = [int(i) for i in args.ports.strip().split(",")]
    my_mux = initialize_mux()
    scales = initialize_scales(ports)
    tare_scales(my_mux, scales)
    input("Press [Enter] to measure a mass. ")
    get_weights(my_mux, scales)


if __name__ == "__main__":
    main()