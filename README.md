# Raspberry Pi Environment Monitor

A python script which retrieves values for temperature, humidity and pressure to monitor it's surrounding environment. 

Ideally, this run on a Raspberry Pi Zero WH, with the sensors connected to it.

* Values are retrieved from a (BME280 sensor)[https://www.amazon.co.uk/GY-BME280-Precision-Barometric-Temperature-Raspberry/dp/B0799JRDKJ/ref=sr_1_4?crid=I5M7YD4U1IU&keywords=bme280&qid=1672434525&s=electronics&sprefix=bme280%2Celectronics%2C97&sr=1-4]
* Values are displayed on a (ST7735 display)[https://www.amazon.co.uk/Display-Control-Horizontal-vertical-Adjustment-default/dp/B07FKX67WN]
* Values are stored in an InfluxDB on a remote server, or another raspberry pi. They can be viewed by connecting InfluxDB to Grafana.
