#!/usr/bin/env python

import RF24
import time


def setup():
    radio = RF24.RF24(22,0)
    #radio = RF24.RF24(RF24.RPI_V2_GPIO_P1_15, RF24.BCM2835_SPI_CS0, RF24.BCM2835_SPI_SPEED_8MHZ)
    address = "00001"
    radio.begin()
    #radio.enableDynamicPayloads()
    radio.setRetries(15,15)
    radio.setDataRate(RF24.RF24_250KBPS)
    radio.openReadingPipe(0, address)
    radio.setPALevel(RF24.RF24_PA_MIN)
    radio.printDetails()
    radio.startListening()
    return radio


def loop(radio):
    if radio.available():
        print("Data available!")
        msg = radio.read(radio.payloadSize)
        print("Received: '%s'" % msg)


if __name__ == "__main__":
    radio = setup()
    while True:
        loop(radio)
        time.sleep(0.1)
