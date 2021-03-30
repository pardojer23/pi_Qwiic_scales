## pi QWiic Scales
The purpose of this package is to 
operate a network of Sparkfun Qwiic enabled scales from a Raspberry Pi.


Hardware Requirements
1. Raspberry pi (tested on model 3b+ running Raspbian GNU/Linux 10 (buster))
2. SparkFun Qwiic HAT for Raspberry Pi https://www.sparkfun.com/products/14459
3. SparkFun Qwiic Mux Breakout - 8 Channel (TCA9548A) https://www.sparkfun.com/products/16784
4. SparkFun Qwiic Scale - NAU7802 https://www.sparkfun.com/products/15242
5. Load cell (tested with Load Cell - 5kg, Straight Bar (TAL220B) https://www.sparkfun.com/products/14729)

Install
To install clone the github repository onto your Raspberry pi, 
`git clone https://github.com/pardojer23/pi_Qwiic_scales.git` 
then from the `pi_Qwiic_scales` directory run the following:
`sudo python3 setup.py install`

Run
usage: Qwiic_scales.py [-h] [-p PORTS] [-c CAL] [-o OUTPUT] [-w WEIGHT_DATA]

optional arguments:

  -h, --help            show this help message and exit
 
  -p PORTS, --ports PORTS
                        list of scale ports on mux (0-7_ separated by commas.
                        
  -c CAL, --cal CAL     path to calibration file
  
  -o OUTPUT, --output OUTPUT
                        path to output directory
                        
  -w WEIGHT_DATA, --weight_data WEIGHT_DATA
                        weight data json file
                        
To run creating a new calibration:

`python3 Qwiic_scales.py --ports 0,1,2,3,4,5,6,7  --output /home/pi/output_directory --weight_data weight_data.json`

To run with an existing calibration:

`python3 Qwiic_scales.py --ports 0,1,2,3,4,5,6,7 --cal /home/pi/calibration_file.json --output /home/pi/output_directory --weight_data weight_data.json`
