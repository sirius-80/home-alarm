# home-alarm
fire-alarm sensors based on arduino and raspberry pi


## Install RF24 driver
```bash
sudo apt-get install build-essential
git clone https://github.com/nRF24/RF24.git
cd RF24/
make
sudo make install
cd pyRF24/
sudo apt-get install python-dev libboost-python-dev 
sudo ln -s /usr/lib/arm-linux-gnueabihf/libboost_python-py34.so /usr/lib/arm-linux-gnueabihf/libboost_python3.so
sudo apt-get install python-setuptools 
sudo apt-get install python3-setuptools 
chmod +x setup.py 
./setup.py build
sudo ./setup.py install
```

## Install influxdb on raspbery pi
https://www.circuits.dk/install-grafana-influxdb-raspberry/
```bash
echo "deb https://repos.influxdata.com/debian stretch stable" | sudo tee /etc/apt/sources.list.d/influxdb.list
curl -sL https://repos.influxdata.com/influxdb.key | sudo apt-key add
sudo apt-get update
sudo apt-get install influxdb
```
* Update influxdb config: enable http and bind-address
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
* Install python support ```python3 -m pip install influxdb```


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
