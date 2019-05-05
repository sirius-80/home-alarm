#!/usr/bin/env python3

import influxdb
import RF24
import time
import datetime
import json



def setup_nrf24():
    #radio = RF24.RF24(22,0)
    radio = RF24.RF24(RF24.RPI_V2_GPIO_P1_15, RF24.BCM2835_SPI_CS0, RF24.BCM2835_SPI_SPEED_8MHZ)
    address = b"00001"
    radio.begin()
    #radio.enableDynamicPayloads()
    radio.setRetries(15,15)
    radio.setDataRate(RF24.RF24_250KBPS)
    radio.openReadingPipe(0, address)
    radio.setPALevel(RF24.RF24_PA_MIN)
    radio.payloadSize = 255
    radio.printDetails()
    radio.startListening()
    return radio


def setup_influxdb_client():
    client = influxdb.InfluxDBClient(host='localhost', port=8086)
    client.switch_database('topics')
    return client


class Measurement:
    def __init__(self, device_id, temperature, smoke_ppm, co_ppm):
        self.device_id = device_id
        self.temperature = temperature
        self.smoke_ppm = smoke_ppm
        self.co_ppm = co_ppm

    @classmethod
    def from_msg(cls, b):
        parts = b.decode("utf-8").strip("\x00").split(",")
        print(parts)
        device_id = parts[0]
        temperature = int(parts[1])
        smoke_ppm = int(parts[2])
        co_ppm = int(parts[3])
        return Measurement(device_id, temperature, smoke_ppm, co_ppm)

    def __str__(self):
        return json.dumps(self.__dict__)

    def to_influxdb_json(self):
        timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        return [
            {
                "measurement": "smoke-detector-events",
                "tags": {
                    "device-id": self.device_id,
                },
                "time": timestamp,
                "fields": {
                    "temperature": self.temperature,
                    "smoke_ppm": self.smoke_ppm,
                    "co_ppm": self.co_ppm
                }
            }
        ]

    
def read_measurement(radio):
    while not radio.available():
        time.sleep(0.1)
        
    print("Data available!")
    msg = radio.read(radio.payloadSize)
    print("Received: '%s'" % msg)
    measurement = Measurement.from_msg(msg)
    print("Received: '%s'" % measurement)
    return measurement


if __name__ == "__main__":
    radio = setup_nrf24()
    client = setup_influxdb_client()
    while True:
        measurement = read_measurement(radio)
        print(measurement.to_influxdb_json())
        client.write_points(measurement.to_influxdb_json())
        
