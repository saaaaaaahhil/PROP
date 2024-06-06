from metadata_extractor.distance import distance_api
from metadata_extractor.places import places_api
import os
from dotenv import load_dotenv
load_dotenv()

def entertainmentDB(vicinity_map, src_lat, src_lng, radius):
    entertainment = ["amusement_center", "amusement_park", "aquarium", "banquet_hall", "bowling_alley", "casino", "community_center", "convention_center", "cultural_center", "dog_park", "event_venue", "hiking_area", "historical_landmark", "marina", "movie_rental", "movie_theater", "national_park", "night_club", "park", "tourist_attraction", "visitor_center", "wedding_venue", "zoo"]

    latlng_dict = places_api(src_lat, src_lng, entertainment, Circular_radius=radius)

    # Temporary list to store entertainment data with distances
    entertainment_data = []

    for latlng, name in latlng_dict.items():
        latitude, longitude = latlng
        distance = distance_api(src_lat, src_lng, latitude, longitude)
        
        if distance is not None:
            # Append each entry to the temporary list with distance as a float value
            distance_float = float(distance.replace(',', '').split()[0])
            entertainment_data.append({
                "Name": name,
                "distance_from_property": distance_float,
                "Longitude": longitude
            })

    # Sort the entertainment data by distance in ascending order
    entertainment_data_sorted = sorted(entertainment_data, key=lambda x: x["distance_from_property"])

    # Convert distance back to string format and add to the vicinity_map
    for data in entertainment_data_sorted:
        data["distance_from_property"] = f"{data['distance_from_property']} km"
        vicinity_map["entertainment"].append(data)

    return vicinity_map

