import requests
import os

API_KEY = os.environ["GOOGLE_MAPS_API_KEY"]

def distance_api(lat, lng, latf, lngf):
    
    url = f"https://maps.googleapis.com/maps/api/distancematrix/json?units=metric&"
#   for pair in latlng_dict:
    parameters = {
        "origins": f"{lat},{lng}",
        "destinations": f"{latf},{lngf}",
        "key": API_KEY
    }
    r = requests.get(url, params=parameters)
    result = r.json()['rows'][0]['elements'][0]
    if 'distance' in result:
        return result["distance"]["text"]
    return None
    # return r.json()

# print(distance_api(21.0989087,79.0925695,21.1290151, 79.1115475,"metrics"))