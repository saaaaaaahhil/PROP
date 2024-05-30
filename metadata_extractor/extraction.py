import requests
import os
from urllib.parse import urlencode
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

def extract_latitude_longitude(address, data_type = 'json'):
  endpoint = f"https://maps.googleapis.com/maps/api/geocode/{data_type}"
  params = {"address" : address, "key" : API_KEY}
  url_params = urlencode(params)
  url=f"{endpoint}?{url_params}"
  r = requests.get(url)
  if r.status_code not in range(200,299):
    return {}
  latlng={}
  try:
    latlng = r.json()['results'][0]['geometry']['location']
  except:
    pass
  return latlng.get("lat"), latlng.get("lng")