from metadata_extractor.distance import distance_api
from metadata_extractor.places import places_api
import os
from dotenv import load_dotenv
load_dotenv()

def shoppingDB(vicinity_map, src_lat, src_lng, radius):
    shopping = ["auto_parts_store","bicycle_store","book_store","cell_phone_store","clothing_store","convenience_store","department_store","discount_store","electronics_store","furniture_store","gift_shop","grocery_store","hardware_store","home_goods_store","home_improvement_store","jewelry_store","liquor_store","market","pet_store","shoe_store","shopping_mall","sporting_goods_store","store","supermarket","wholesaler"]
    latlng_dict = places_api(src_lat, src_lng, shopping, Circular_radius=radius)

    # Temporary list to store shopping data with distances
    shopping_data = []

    for latlng, name in latlng_dict.items():
        latitude, longitude = latlng
        distance = distance_api(src_lat, src_lng, latitude, longitude)
        


        if distance is not None:
            # Append each entry to the temporary list with distance as a float value
            distance_float = float(distance.replace(',', '').split()[0])
            shopping_data.append({
                "Name": name,
                "distance_from_property": distance_float, 
                "Latitude": latitude,
                "Longitude": longitude
            })

    # Sort the shopping data by distance in ascending order
    shopping_data_sorted = sorted(shopping_data, key=lambda x: x["distance_from_property"])

    # Convert distance back to string format and add to the vicinity_map
    for data in shopping_data_sorted:
        data["distance_from_property"] = f"{data['distance_from_property']} km"
        vicinity_map["shopping"].append(data)

    return vicinity_map
