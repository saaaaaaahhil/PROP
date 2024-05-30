from metadata_extractor.distance import distance_api
from metadata_extractor.places import places_api
import os
from dotenv import load_dotenv
load_dotenv()

def restaurantDB(vicinity_map, src_lat, src_lng, radius):
    restaurant = ["american_restaurant","bakery","bar","barbecue_restaurant","brazilian_restaurant","breakfast_restaurant","brunch_restaurant","cafe","chinese_restaurant","coffee_shop","fast_food_restaurant","french_restaurant","greek_restaurant","hamburger_restaurant","ice_cream_shop","indian_restaurant","indonesian_restaurant","italian_restaurant","japanese_restaurant","korean_restaurant", "lebanese_restaurant","meal_delivery","meal_takeaway","mediterranean_restaurant","mexican_restaurant","middle_eastern_restaurant","pizza_restaurant","ramen_restaurant","restaurant","sandwich_shop","seafood_restaurant","spanish_restaurant","steak_house","sushi_restaurant","thai_restaurant","turkish_restaurant","vegan_restaurant","vegetarian_restaurant","vietnamese_restaurant"]
    latlng_dict = places_api(src_lat, src_lng, restaurant, Circular_radius=radius)

    # Temporary list to store restaurant data with distances
    restaurant_data = []

    for latlng, name in latlng_dict.items():
        latitude, longitude = latlng
        distance = distance_api(src_lat, src_lng, latitude, longitude)
        
        if distance is not None:
            # Append each entry to the temporary list with distance as a float value
            restaurant_data.append({
                "Name": name,
                "distance_from_property": float(distance.split()[0]), 
                "Latitude": latitude,
                "Longitude": longitude
            })

    # Sort the restaurant data by distance in ascending order
    restaurant_data_sorted = sorted(restaurant_data, key=lambda x: x["distance_from_property"])

    # Convert distance back to string format and add to the vicinity_map
    for data in restaurant_data_sorted:
        data["distance_from_property"] = f"{data['distance_from_property']} km"
        vicinity_map["restaurant"].append(data)

    return vicinity_map
