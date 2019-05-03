#!/usr/bin/env python3

import influxdb

client = influxdb.InfluxDBClient(host='localhost', port=8086)
client.switch_database('topics')
json_body = [
    {
        "measurement": "smoke-detector-events",
        "tags": {
            "device-id": "6c89f539-71c6-490d-a28d-6c5d84c0ee2f"
        },
        "time": "2019-05-03T08:01:00Z",
        "fields": {
            "temperature": 17,
            "smoke_ppm": 10,
            "co_ppm": 12
        }
    },
    {
        "measurement": "smoke-detector-events",
        "tags": {
            "device-id": "6c89f539-71c6-490d-a28d-6c5d84c0ee2f"
        },
        "time": "2019-05-03T08:02:00Z",
        "fields": {
            "temperature": 18,
            "smoke_ppm": 12,
            "co_ppm": 10
        }
    },
    {
        "measurement": "smoke-detector-events",
        "tags": {
            "device-id": "6c89f539-71c6-490d-a28d-6c5d84c0ee2f"
        },
        "time": "2019-05-03T08:03:00Z",
        "fields": {
            "temperature": 17,
            "smoke_ppm": 6,
            "co_ppm": 3
        }
    }
    ]
#client.write_points(json_body)
results = client.query('SELECT * FROM "topics"."autogen"."smoke-detector-events"')
print(results.raw)
