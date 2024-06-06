from metadata_extractor.distance import distance_api
from metadata_extractor.places import places_api
import os
from dotenv import load_dotenv
load_dotenv()

def educationDB(vicinity_map, src_lat, src_lng, radius):
    education = ["school", "university", "preschool", "primary_school", "secondary_school"]
    latlng_dict = places_api(src_lat, src_lng, education, Circular_radius=radius)

    # Temporary list to store education data with distances
    education_data = []

    for latlng, name in latlng_dict.items():
        latitude, longitude = latlng
        distance = distance_api(src_lat, src_lng, latitude, longitude)

        if distance is not None:
            # Append each entry to the temporary list with distance as a float value
            distance_float = float(distance.replace(',', '').split()[0])
            education_data.append({
                "Name": name,
                "distance_from_property": distance_float,  
                "Latitude": latitude,
                "Longitude": longitude
            })

    # Sort the education data by distance in ascending order
    education_data_sorted = sorted(education_data, key=lambda x: x["distance_from_property"])

    # Convert distance back to string format and add to the vicinity_map
    for data in education_data_sorted:
        data["distance_from_property"] = f"{data['distance_from_property']} km"
        vicinity_map["education"].append(data)

    return vicinity_map
