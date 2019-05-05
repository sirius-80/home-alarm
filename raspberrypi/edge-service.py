#!/usr/bin/env python

import time
import influxdb
import RF24
import datetime
import json
from enum import Enum
import traceback
import threading


class TimeoutMonitor:
    """Simple monitor that will trigger given alert_function when no data is received from sensors anymore."""
    def __init__(self, timeout_sec, alert_function, *args):
        self._timeout_sec = timeout_sec
        self._reset = False
        self._alert_function = alert_function
        self._args = args
        self._active = False
        self._thread = threading.Thread(target=self._run)

    def start(self):
        self._active = True
        self._thread.start()

    def stop(self):
        print("Stopping monitor...")
        self._active = False
        self._thread.join()

    def _run(self):
        while self._active:
            try:
                self._monitor()
                self._reset = False
            except TimeoutError:
                self._alert_function(*self._args)
        print("Monitor stops")

    def reset(self):
        self._reset = True

    def _monitor(self):
        start_time = time.time()
        while not self._reset and self._active:
            now = time.time()
            if self._timeout_sec < (now - start_time):
                raise TimeoutError
            time.sleep(1)


class RadioReceiver:
    """Provide access to the nrf2401+ radio device"""
    def __init__(self, listening_address=b"00001"):
        self.radio = RF24.RF24(RF24.RPI_V2_GPIO_P1_15, RF24.BCM2835_SPI_CS0, RF24.BCM2835_SPI_SPEED_8MHZ)
        # self.radio = RF24.RF24(22,0)
        self.radio.begin()
        self.radio.setRetries(15, 15)
        self.radio.setDataRate(RF24.RF24_250KBPS)
        self.radio.openReadingPipe(0, listening_address)
        self.radio.setPALevel(RF24.RF24_PA_MIN)
        self.radio.printDetails()
        self.radio.startListening()

    def read_measurement(self):
        """Waits for next message and returns it as a binary string"""
        while not self.radio.available():
            time.sleep(1)

        print("Data available!")
        msg = self.radio.read(self.radio.payloadSize)
        print("Received: '%s'" % msg)
        return msg


def convert_radio_message_to_measurement(msg):
    """Constructs a Measurement object from a binary sensor message"""
    parts = msg.decode("utf-8").strip("\x00").split(",")
    print(parts)
    device_id = parts[0]
    temperature = int(parts[1])
    smoke_ppm = int(parts[2])
    co_ppm = int(parts[3])
    return Measurement(device_id, temperature, smoke_ppm, co_ppm)


class InfluxDbClient:
    def __init__(self):
        self.client = influxdb.InfluxDBClient(host='localhost', port=8086)
        self.client.switch_database('topics')

    def add_measurement(self, measurement):
        """Converts this Measurement to influxdb compatible json"""
        timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        data = [
            {
                "measurement": "smoke-detector-events",
                "tags": {
                    "device-id": measurement.device_id,
                },
                "time": timestamp,
                "fields": {
                    "temperature": measurement.temperature,
                    "smoke_ppm": measurement.smoke_ppm,
                    "co_ppm": measurement.co_ppm
                }
            }
        ]
        self.client.write_points(data)


class Measurement:
    """Represents a single measurement from the sensor device"""
    def __init__(self, device_id, temperature, smoke_ppm, co_ppm):
        self.device_id = device_id
        self.temperature = temperature
        self.smoke_ppm = smoke_ppm
        self.co_ppm = co_ppm

    def __str__(self):
        return json.dumps(self.__dict__)


class DeviceState(Enum):
    OFFLINE = 0
    ONLINE = 1


class SensorDevice:
    def __init__(self, id):
        self.id = id
        self.state = DeviceState.OFFLINE

    def offline(self):
        if self.state == DeviceState.ONLINE:
            print("Sensor %s went offline!" % self.id)
        self.state = DeviceState.OFFLINE

    def online(self):
        if self.state == DeviceState.OFFLINE:
            print("Sensor %s came online!" % self.id)
        self.state = DeviceState.ONLINE


class ExternalMessagingService:
    """"Proxy for Google Cloud Messaging or comparable push-message service.
    TODO: Implement!"""
    def __init__(self):
        pass

    def send(self, message):
        print("TODO: Implement sending alert to external messaging service: '%s'" % message)


class EdgeService:
    def __init__(self, sensor_device_id_list):
        self.message_service = ExternalMessagingService()
        self.sensors = {}
        self.monitors = {}
        for sensor_id in sensor_device_id_list:
            sensor = SensorDevice(sensor_id)
            self.sensors[sensor_id] = sensor
            monitor = TimeoutMonitor(20, self._handle_sensor_timeout, sensor)
            self.monitors[sensor_id] = monitor
            monitor.start()
        self.sensor_device_id_list = sensor_device_id_list
        self.radio_receiver = RadioReceiver()
        self.database = InfluxDbClient()

    def _handle_sensor_timeout(self, sensor):
        if sensor.state == DeviceState.ONLINE:
            message = "Sensor with id %s timed out, taking it offline!" % sensor.id
        else:
            message = "Sensor with id %s is still offline..." % sensor.id
        sensor.offline()
        self.message_service.send(message)

    def run(self):
        active = True
        while active:
            try:
                msg = self.radio_receiver.read_measurement()
                measurement = convert_radio_message_to_measurement(msg)

                # The device seems to be online!
                self.monitors[measurement.device_id].reset()
                self.sensors[measurement.device_id].online()

                # store the data
                self.database.add_measurement(measurement)
            except KeyboardInterrupt:
                print("Keyboard interrupt! Stopping service...")
                active = False
                for monitor in self.monitors.values():
                    monitor.stop()
            except Exception as err:
                print("ERROR: %s" % err)
                traceback.print_exc()


if __name__ == "__main__":
    service = EdgeService(["6c89f539", "dummy"])
    service.run()
