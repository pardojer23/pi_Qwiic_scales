import qwiic
import time
import PyNAU7802
import smbus2
import argparse
def initialize_mux(ports):
    my_mux = qwiic.QwiicTCA9548A()
    # disable all channels
    my_mux.disable_channels([0, 1, 2, 3, 4, 5, 6, 7])
    # enable ports
    my_mux.enable_channels(ports)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--ports",
                        help="list of scale ports on mux (0-7_ separated by commas.")
    args = parser.parse_args()
    ports = [int(i) for i in args.ports.strip().split(",")]
    initialize_mux(ports)

if __name__ == "__main__":
    main()