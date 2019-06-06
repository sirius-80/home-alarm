#!/usr/bin/env python

import argparse
import time
import influxdb
import RF24
import datetime
import json
from enum import Enum
import traceback
import threading
import requests
import logging
import logging.handlers
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore


cred = credentials.Certificate('home-monitor-bb687-firebase-adminsdk-t4efc-70544a2138.json')
firebase_admin.initialize_app(cred)


class FirestoreClient:
    def __init__(self):
        self.db = firestore.client()

    def add_measurement(self, measurement):
        sensor_id = measurement.device_id
        measurement_doc_ref = self.db.collection(u'sensors').document(sensor_id).collection(u'measurements')
        measurement_id = str(measurement.timestamp.timestamp())
        measurement_doc_ref.document(measurement_id).set(measurement.dict())

    def update_sensor_data(self, sensor):
        sensor_doc_ref = self.db.collection(u'sensors').document(sensor.id)
        sensor_doc_ref.set(sensor.dict(), merge=True)

    def get_sensor_ids(self):
        return [sensor.id for sensor in self.db.collection(u'sensors').get()]


class TimeoutMonitor:
    """Simple monitor that will trigger given alert_function when no data is received from sensors anymore."""
    def __init__(self, timeout_sec, alert_function, *args):
        """Sets up the monitor. Upon a time-out, the alert_function will be called, with the provided *args."""
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
        logger.info("Stopping monitor...")
        self._active = False
        self._thread.join()

    def _run(self):
        while self._active:
            try:
                self._monitor()
                self._reset = False
            except TimeoutError:
                self._alert_function(*self._args)
        logger.info("Monitor stops")

    def reset(self):
        """Resets the monitor (restarts the time-out sequence).
        Must be called periodically to prevent a time-out."""
        self._reset = True

    def _monitor(self):
        """Single monitoring loop: either stops by reset, or generates a time-out."""
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

        logger.debug("Data available!")
        msg = self.radio.read(self.radio.payloadSize)
        logger.debug("Received: '%s'" % msg)
        return msg


def convert_radio_message_to_measurement(msg):
    """Constructs a Measurement object from a binary sensor message"""
    parts = msg.decode("utf-8").strip("\x00").split(",")
    logger.debug(str(parts))
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
        data = [
            {
                "measurement": "smoke-detector-events",
                "tags": {
                    "device-id": measurement.device_id,
                },
                "time": measurement.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
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
        self.timestamp = datetime.datetime.utcnow()

    def __str__(self):
        return json.dumps(self.__dict__)

    def dict(self):
        return self.__dict__.copy()


class DeviceState(Enum):
    """Sensor devices can be either ONLINE or OFFLINE"""
    OFFLINE = 0
    ONLINE = 1


class SensorDevice:
    """Simple class to manaage the state of a sensor-device."""
    def __init__(self, id):
        self.id = id
        self.state = DeviceState.OFFLINE
        self.up_since = None

    def offline(self):
        if self.state == DeviceState.ONLINE:
            logger.warning("Sensor %s went offline!", self.id)
        self.state = DeviceState.OFFLINE

    def online(self):
        if self.state == DeviceState.OFFLINE:
            self.up_since = datetime.datetime.utcnow()
            logger.warning("Sensor %s came online!", self.id)
        self.state = DeviceState.ONLINE

    def dict(self):
        return {"id": self.id,
                "state": self.state.name,
                "up_since": self.up_since}


class ExternalMessagingService:
    """"Proxy for Google Firebase Messaging or comparable push-message service."""
    def __init__(self, base_url):
        self.base_url = base_url

    def send_alert(self, title, body):
        self._send("alerts", title, body)

    def send_notification(self, title, body):
        self._send("notes", title, body)

    def _send(self, topic, title, body):
        logger.info("Sending %s to external messaging service: '%s:%s'", topic, title, body)
        params = {"topic": topic, "title": title, "body": body}
        logger.debug(str(requests.get(self.base_url, params=params)))


class EdgeService:
    """Monitors all sensor devices, forwards received measurements to the database, and
    triggers the message service when a sensor device times out."""
    def __init__(self, sensor_device_id_list, base_url_msg_svc):
        logger.info("Starting EdgeService. Messages will be sent to %s", base_url_msg_svc)
        self.message_service = ExternalMessagingService(base_url_msg_svc)
        self.sensors = {}
        self.monitors = {}
        for sensor_id in sensor_device_id_list:
            logger.info("Adding sensor to monitor: %s", sensor_id)
            sensor = SensorDevice(sensor_id)
            self.sensors[sensor_id] = sensor
            monitor = TimeoutMonitor(60, self._handle_sensor_timeout, sensor)
            self.monitors[sensor_id] = monitor
            monitor.start()
        self.sensor_device_id_list = sensor_device_id_list
        self.radio_receiver = RadioReceiver()
        self.influx = InfluxDbClient()
        self.firestore = FirestoreClient()

    def _handle_sensor_timeout(self, sensor):
        if sensor.state == DeviceState.ONLINE:
            message = "Sensor with id %s timed out. It is now considered to be offline!" % sensor.id
            logger.warning(message)
            sensor.offline()
            self.firestore.update_sensor_data(sensor)
            self.message_service.send_notification("Device status changed", message)
        else:
            logger.debug("Sensor with id %s is still offline...", sensor.id)

    def run(self):
        active = True
        self.message_service.send_alert("Service status changed", "The edge-service is up. Your devices are being monitored.")
        while active:
            try:
                msg = self.radio_receiver.read_measurement()
                measurement = convert_radio_message_to_measurement(msg)
                logger.debug("Received measurement: %s", measurement)

                # The device seems to be online!
                self.monitors[measurement.device_id].reset()
                sensor = self.sensors[measurement.device_id]
                if sensor.state == DeviceState.OFFLINE:
                    sensor.online()
                    self.message_service.send_notification("Device status changed", "Sensor with id %s came online." % sensor.id)
                    self.firestore.update_sensor_data(sensor)

                # check the data for possible fire or high CO concentration
                self.check_data_alerts(measurement)

                # Store the data
                self.influx.add_measurement(measurement)
                self.firestore.add_measurement(measurement)
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt! Stopping service...")
                self.message_service.send_alert("Service status changed", "The edge-service is going down! Your devices are no longer being monitored!")
                active = False
                for monitor in self.monitors.values():
                    monitor.stop()
            except Exception as err:
                logger.error(str(err))
                traceback.print_exc()

    def check_data_alerts(self, measurement):
        if measurement.temperature > 50 or measurement.smoke_ppm > 600:
            self.message_service.send_alert("Probably fire!", "The temperature is %d degrees C, smoke is at %d ppm" % (measurement.temperature, measurement.smoke_ppm))
        elif measurement.co_ppm > 200:
            self.message_service.send_alert("Carbon-monoxide alert!", "High amount of CO in the air (%d ppm)" % measurement.co_ppm)


if __name__ == "__main__":
    LOG_FILENAME = "/tmp/edge-service.log"
    LOG_LEVEL = logging.INFO
    parser = argparse.ArgumentParser(description="Home-alarm edge service")
    parser.add_argument("-l", "--log", help="file to write log to (default '" + LOG_FILENAME + "')")
    parser.add_argument("-b", "--base-url", help="url for firebase addMessage function service")
    args = parser.parse_args()
    if args.log:
        LOG_FILENAME = args.log
    logger = logging.getLogger(__name__)
    logger.setLevel(LOG_LEVEL)
    handler = logging.handlers.TimedRotatingFileHandler(LOG_FILENAME, when="midnight", backupCount=3)
    formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


    try:
        service = EdgeService(FirestoreClient().get_sensor_ids(), args.base_url)
        service.run()
    except KeyboardInterrupt:
        logger.info("Stopping edge service (keyboard interrupt)")
    except:
        logger.exception("Something went horribly wrong!")
    
    logger.info("Bye")

