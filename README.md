# home-alarm
fire-alarm sensors based on arduino and raspberry pi

## TODO
* Integrate actual CO, smoke and temperature sensors on arduino
* Create android app
* Integrate Google firebase Messaging in app and rpi edge device
* ...
* minimize power-consumption of arduino + sensors
* autostart apps on raspberry pi
** Grafana
** Edge service

## Make python3 the default using update-alternatives
```
$ sudo update-alternatives --install /usr/bin/python python /usr/bin/python2 1
update-alternatives: using /usr/bin/python2 to provide /usr/bin/python (python) in auto mode
$ sudo update-alternatives --install /usr/bin/python python /usr/bin/python3 2
update-alternatives: using /usr/bin/python3 to provide /usr/bin/python (python) in auto mode
$ # As we'given python3 a higher priority, it should now be the default
$ python --version
Python 3.5.3
$ # Optionally change the default, using update-alternatives
$ sudo update-alternatives --config python
There are 2 choices for the alternative python (providing /usr/bin/python).

  Selection    Path              Priority   Status
------------------------------------------------------------
* 0            /usr/bin/python3   2         auto mode
  1            /usr/bin/python2   1         manual mode
  2            /usr/bin/python3   2         manual mode

Press <enter> to keep the current choice[*], or type selection number:
```

## Install RF24 driver
```bash
sudo apt-get install build-essential
git clone https://github.com/nRF24/RF24.git
cd RF24/
make
sudo make install
cd pyRF24/
sudo apt-get install python-dev libboost-python-dev 
# Note: the name of the so-file to link depends on the version of python 
sudo ln -s /usr/lib/arm-linux-gnueabihf/libboost_python-py35.so /usr/lib/arm-linux-gnueabihf/libboost_python3.so
sudo apt-get install python-setuptools 
sudo apt-get install python3-setuptools 
python3 setup.py build
sudo python3 setup.py install
```

## Install influxdb on raspbery pi
https://www.circuits.dk/install-grafana-influxdb-raspberry/
```bash
echo "deb https://repos.influxdata.com/debian stretch stable" | sudo tee /etc/apt/sources.list.d/influxdb.list
curl -sL https://repos.influxdata.com/influxdb.key | sudo apt-key add
sudo apt-get update
sudo apt-get install influxdb
```
* Update influxdb config: enable http and set bind-address to port 8086
```sudo vi /etc/influxdb/influxdb.conf```
```
...
[http]
  # Determines whether HTTP endpoint is enabled.
  enabled = true

  # Determines whether the Flux query endpoint is enabled.
  # flux-enabled = false

  # Determines whether the Flux query logging is enabled.
  # flux-log-enabled = false

  # The bind address used by the HTTP service.
  bind-address = ":8086"

  # Determines whether user authentication is enabled over HTTP/HTTPS.
  # auth-enabled = false
  ...
```
* Start influx deamon ```sudo service influxdb start```
* Install python support ```sudo python3 -m pip install influxdb```


## Configure influxdb
* Create database
```
influx

CREATE DATABASE topics
```
* Check that it works with browser: http://raspberrypi:8086 (should give a 404 error page)


## Install grafana on raspberry pi
```
sudo apt-get install apt-transport-https curl
curl https://bintray.com/user/downloadSubjectPublicKey?username=bintray | sudo apt-key add -
echo "deb https://dl.bintray.com/fg2it/deb jessie main" | sudo tee -a /etc/apt/sources.list.d/grafana.list
sudo apt-get update && sudo apt-get install grafana
```

## Configure grafana
* Add influxdb as datasource
* Create dashboard
