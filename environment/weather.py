#!/usr/bin/env python3
import logging
import sys
import requests
from influxdb import InfluxDBClient

LATITUDE="52.52"
LONGITUDE="13.41"

logging.basicConfig(
    format='%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')

client = InfluxDBClient(host="192.168.0.2", port=8086, database='environment')

# pylint: disable=line-too-long
url = f"https://api.open-meteo.com/v1/forecast?latitude={LATITUDE}&longitude={LONGITUDE}&current_weather=true"
try:
    response = requests.get(url, timeout=5)
except: # pylint: disable=bare-except
    logging.error("Unable to retrieve weather data")
    sys.exit(1)
data = response.json()

current_time = data["current_weather"]["time"]
json_body = [
        {
            "measurement": "outdoor_temperature",
            "time": current_time,
            "fields": {
                "Float_value": data["current_weather"]["temperature"]
            }
        },
        {
            "measurement": "windspeed",
            "time": current_time,
            "fields": {
                "Float_value": data["current_weather"]["windspeed"]
            }
        },
        {
            "measurement": "winddirection",
            "time": current_time,
            "fields": {
                "Float_value": data["current_weather"]["winddirection"]
            }
        }
    ]


try:
    client.write_points(json_body)
except requests.ConnectionError:
    logging.error("Unable to connect to InfluxDB")
