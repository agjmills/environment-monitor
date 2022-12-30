#!/usr/bin/env python3

import time
import colorsys
import sys
import ST7735
from requests import ConnectionError
from influxdb import InfluxDBClient
from bme280 import BME280
from subprocess import PIPE, Popen
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from fonts.ttf import RobotoMedium as UserFont
import logging

logging.basicConfig(
    format='%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')

logging.info("""monitor.py - Displays readings from BME280 sensors, output to ST7735 displays.

Press Ctrl+C to exit!

""")

# BME280 temperature/pressure/humidity sensor
bme280 = BME280()

# Init display
st7735 = ST7735.ST7735(port=0, cs=1, dc=9, backlight=12, rotation=270, spi_speed_hz=10000000)
st7735.begin()

WIDTH = st7735.width
HEIGHT = st7735.height

# Set up canvas and font
img = Image.new('RGB', (WIDTH, HEIGHT), color=(0, 0, 0))
draw = ImageDraw.Draw(img)
font_size_small = 10
font_size_large = 15
font = ImageFont.truetype(UserFont, font_size_large)
smallfont = ImageFont.truetype(UserFont, font_size_small)
x_offset = 2
y_offset = 2

message = ""
top_pos = 25

variables = [
                "temperature",
                "pressure",
                "humidity"
            ]

units = [
            "C",
            "hPa",
            "%"
        ]

# Warning limits, if the value exceeds these, change the colour of the font
limits = [[4, 18, 28, 35],
          [250, 650, 1013.25, 1015],
          [20, 30, 60, 70]]

# RGB palette for values on the combined screen
palette = [(0, 0, 255),           # Dangerously Low
           (0, 255, 255),         # Low
           (0, 255, 0),           # Normal
           (255, 255, 0),         # High
           (255, 0, 0)]           # Dangerously High

values = {}

client = InfluxDBClient(host="192.168.0.2", port=8086, database='environment')


# Iterate through the variables List, retrieve the value from the data array, display 
# in the appropriate colour
def display_everything():
    draw.rectangle((0, 0, WIDTH, HEIGHT), (0, 0, 0))
    column_count = 1
    row_count = (len(variables) / column_count)
    for i in range(len(variables)):
        variable = variables[i]
        data_value = values[variable][-1]
        unit = units[i]
        x = x_offset + ((WIDTH // column_count) * (i // row_count))
        y = y_offset + ((HEIGHT / row_count) * (i % row_count))
        message = "{}: {:.1f} {}".format(variable, data_value, unit)
        lim = limits[i]
        rgb = palette[0]
        for j in range(len(lim)):
            if data_value > lim[j]:
                rgb = palette[j + 1]
        draw.text((x, y), message, font=font, fill=rgb)
    st7735.display(img)

# Saves the data to be used in the display
def save_data(idx, data):
    variable = variables[idx]
    # Maintain length of list
    values[variable] = values[variable][1:] + [data]
    unit = units[idx]
    message = "{}: {:.1f} {}".format(variable[:4], data, unit)
    logging.debug(message)

# Get the temperature of the CPU for compensation
def get_cpu_temperature():
    process = Popen(['vcgencmd', 'measure_temp'], stdout=PIPE, universal_newlines=True)
    output, _error = process.communicate()
    return float(output[output.index('=') + 1:output.rindex("'")])


def main():
    # Tuning factor for compensation. Decrease to adjust the
    # temperature down, and increase to adjust up
    factor = 2.25

    cpu_temps = [get_cpu_temperature()] * 5

    for v in variables:
        values[v] = [1] * WIDTH

    while True:
        current_time = time.strftime("%Y-%m-%dT%H:%M:%SZ")
        json_body = []
        # Everything on one screen
        cpu_temp = get_cpu_temperature()
        # Smooth out with some averaging to decrease jitter
        cpu_temps = cpu_temps[1:] + [cpu_temp]
        avg_cpu_temp = sum(cpu_temps) / float(len(cpu_temps))
        raw_temp = bme280.get_temperature()
        raw_data = raw_temp - ((avg_cpu_temp - raw_temp) / factor)
        save_data(0, raw_data)
        display_everything()
        json_body.append({
                "measurement": "temperature",
                "time": current_time,
                "fields": {
                    "Float_value": raw_data
                }
            })

        raw_data = bme280.get_pressure()
        save_data(1, raw_data)
        display_everything()
        json_body.append({
                "measurement": "pressure",
                "time": current_time,
                "fields": {
                    "Float_value": raw_data
                }
            })

        raw_data = bme280.get_humidity()
        save_data(2, raw_data)
        display_everything()
        json_body.append({
                "measurement": "humidity",
                "time": current_time,
                "fields": {
                    "Float_value": raw_data
                }
            })

        try:
            client.write_points(json_body)
        except ConnectionError:
            logging.info("Unable to connect to InfluxDB")
        logging.debug(json_body)
        time.sleep(1)

# Loading screen to allow the temperature sensor to stabilise and the network to be up
def startup():
    message = ""
    for x in range(10):
        bme280.get_temperature()
        bme280.get_pressure()
        bme280.get_humidity()
        time.sleep(1)

        # New canvas to draw on.
        draw = ImageDraw.Draw(img)

        # Text settings.
        font_size = 40
        font = ImageFont.truetype(UserFont, font_size)
        text_colour = (255, 255, 255)
        back_colour = (235, 64, 52)

        message = message + "."
        size_x, size_y = draw.textsize(message, font)
        x = (WIDTH - size_x) / 2
        y = (HEIGHT / 2) - (size_y / 2)

        draw.rectangle((0, 0, 160, 80), back_colour)
        draw.text((x, y), message, font=font, fill=text_colour)
        st7735.display(img)

            

if __name__ == "__main__":
    try:
        startup()
        main()
    except KeyboardInterrupt:
        st7735.
        sys.exit(0)
