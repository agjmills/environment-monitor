#!/usr/bin/env python3

import time
import sys
import logging
from subprocess import PIPE, Popen
import ST7735
import requests
from influxdb import InfluxDBClient
from bme280 import BME280
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from fonts.ttf import RobotoMedium as UserFont

logging.basicConfig(
    format='%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')

logging.info("""monitor.py - Displays readings from a BME280 sensor, output to a ST7735 display.

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
font = ImageFont.truetype(UserFont, 15)
X_OFFSET = 2
Y_OFFSET = 2

MESSAGE = ""
TOP_POS = 25

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

# Iterate through the variables List, retrieve the value from the values Dict, display
# in the appropriate colour
def display_everything():
    draw.rectangle((0, 0, WIDTH, HEIGHT), (0, 0, 0))
    column_count = 1
    row_count = (len(variables) / column_count)
    for index, variable in enumerate(variables):
        data_value = values[variable]
        unit = units[index]
        x_center = X_OFFSET + ((WIDTH // column_count) * (index// row_count))
        y_center = Y_OFFSET + ((HEIGHT / row_count) * (index % row_count))
        message = f"{variable}: {data_value} {unit}"
        variable_limits = limits[index]
        rgb = palette[0]
        for jindex, limit in enumerate(variable_limits):
            if data_value > limit:
                rgb = palette[jindex + 1]
        draw.text((x_center, y_center), message, font=font, fill=rgb)
    st7735.display(img)


def save_data(idx, data):
    variable = variables[idx]
    # Maintain length of list
    values[variable] = data
    unit = units[idx]
    message = f"{variable[:4]}: {data} {unit}"
    logging.debug(message)

# Get the temperature of the CPU for compensation
def get_cpu_temperature():
    with Popen(['vcgencmd', 'measure_temp'], stdout=PIPE, universal_newlines=True) as process:
        output, _error = process.communicate()
    return float(output[output.index('=') + 1:output.rindex("'")])


# try to write the data to influxdb with the current timestamp
def write_to_influxdb():
    json_body = []
    current_time = time.strftime("%Y-%m-%dT%H:%M:%SZ")

    for variable in variables:
        json_body.append({
                "measurement": variable,
                "time": current_time,
                "fields": {
                    "Float_value": values[variable]
                }
            }
        )

    logging.debug(json_body)
    try:
        client.write_points(json_body)
    except requests.ConnectionError:
        logging.error("Unable to connect to InfluxDB")


# try to flush the data to the display and influxdb in one operation
def flush_data():
    display_everything()
    write_to_influxdb()


def main():
    # Tuning factor for compensation. Decrease to adjust the
    # temperature down, and increase to adjust up
    factor = 2.25

    cpu_temps = [get_cpu_temperature()] * 5

    for variable in variables:
        values[variable] = [1] * WIDTH

    while True:
        # Everything on one screen
        cpu_temp = get_cpu_temperature()
        # Smooth out with some averaging to decrease jitter
        cpu_temps = cpu_temps[1:] + [cpu_temp]
        avg_cpu_temp = sum(cpu_temps) / float(len(cpu_temps))
        raw_temp = bme280.get_temperature()
        temperature = raw_temp - ((avg_cpu_temp - raw_temp) / factor)
        save_data(0, temperature)

        pressure = bme280.get_pressure()
        save_data(1, pressure)

        humidity = bme280.get_humidity()
        save_data(2, humidity)

        flush_data()
        time.sleep(1)


# Loading screen to allow the temperature sensor to stabilise and the network to be up
def startup():
    message = "Loading"
    for _ in range(5):
        bme280.get_temperature()
        bme280.get_pressure()
        bme280.get_humidity()
        time.sleep(2)

        # Text settings.
        loading_font = ImageFont.truetype(UserFont, 40)
        text_colour = (255, 255, 255)
        back_colour = (235, 64, 52)

        message = message + "."
        size_x, size_y = draw.textsize(message, loading_font)
        x_center = (WIDTH - size_x) / 2
        y_center = (HEIGHT / 2) - (size_y / 2)

        draw.rectangle((0, 0, 160, 80), back_colour)
        draw.text((x_center, y_center), message, font=loading_font, fill=text_colour)
        st7735.display(img)


if __name__ == "__main__":
    try:
        startup()
        main()
    except:
        st7735.set_backlight(0)
        sys.exit(0)
