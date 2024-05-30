from metadata_extractor.distance import distance_api
from metadata_extractor.places import places_api
import os
from dotenv import load_dotenv
load_dotenv()

def healthcareDB(vicinity_map, src_lat, src_lng, radius):
    healthcare = ["dental_clinic", "doctor", "drugstore", "hospital", "medical_lab", "pharmacy", "physiotherapist", "spa"]
    latlng_dict = places_api(src_lat, src_lng, healthcare, Circular_radius=radius)

    # Temporary list to store healthcare data with distances
    healthcare_data = []

    for latlng, name in latlng_dict.items():
        latitude, longitude = latlng
        distance = distance_api(src_lat, src_lng, latitude, longitude)
        

        if distance is not None:
            
            # Remove comma and convert to float
            distance_float = float(distance.replace(',', '').split()[0])

            # Append each entry to the temporary list with distance as a float value
            healthcare_data.append({
                "Name": name,
                "distance_from_property": distance_float, 
                "Latitude": latitude,
                "Longitude": longitude
            })

    # Sort the healthcare data by distance in ascending order
    healthcare_data_sorted = sorted(healthcare_data, key=lambda x: x["distance_from_property"])

    # Convert distance back to string format and add to the vicinity_map
    for data in healthcare_data_sorted:
        data["distance_from_property"] = f"{data['distance_from_property']} km"
        vicinity_map["healthcare"].append(data)

    return vicinity_map

