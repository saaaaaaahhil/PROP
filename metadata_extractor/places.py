import requests
import os
from dotenv import load_dotenv
from metadata_extractor.extraction import extract_latitude_longitude
load_dotenv()
API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

def places_api(lat, lng, keywords, Circular_radius):
    places_endpoint = "https://places.googleapis.com/v1/places:searchNearby/"
    body = {
        "includedTypes": keywords,
        "rankPreference":'DISTANCE',
        "locationRestriction": {
        "circle": {
            "center": {
            "latitude": lat,
            "longitude": lng},
            "radius": Circular_radius
        }
        }
    }
    headers = {
        'Content-Type': 'application/json',
        'X-Goog-Api-Key': f'{API_KEY}',
        'X-Goog-FieldMask': 'places.displayName'
    }
    response = requests.post(places_endpoint, json=body, headers=headers).json()
    
    name_coordinate_dict = {}
    # Arrange them in ascending order of distance, append first 10 results
    if 'places' in response:
        for i in range(0,len(response['places'])):
            name = response['places'][i]['displayName']['text']
            name_coordinate_dict[extract_latitude_longitude(name)]=name
    return name_coordinate_dict

