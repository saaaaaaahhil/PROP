import os
import requests


API_KEY = os.environ["GOOGLE_MAPS_API_KEY"]

def aqi(src_lat, src_lng):
    url = f"https://airquality.googleapis.com/v1/currentConditions:lookup?key={API_KEY}"
    body = {
            "location": {
                "latitude": f"{src_lat}",
                "longitude": f"{src_lng}"
            }
        }
    headers = {
        "Content-Type": "application/json"
    }
    r = requests.post(url, json=body, headers=headers)
    if 'indexes' in r.json():
        for i in range(0,len(r.json()['indexes'])):
            return r.json()['indexes'][0]['aqi']
    

