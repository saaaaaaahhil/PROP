from metadata_extractor.aqi import aqi 
from metadata_extractor.educationDB import educationDB
from metadata_extractor.entertainmentDB import entertainmentDB
from metadata_extractor.healthcareDB import healthcareDB
from metadata_extractor.landmarkDB import landmarkDB
from metadata_extractor.places import places_api
from metadata_extractor.extraction import extract_latitude_longitude
from metadata_extractor.distance import distance_api
from metadata_extractor.restaurantDB import restaurantDB
from metadata_extractor.shoppingDB import shoppingDB
from routes.mongo_db_functions import insert_metadata_to_db
from fastapi import APIRouter
from fastapi.responses import JSONResponse
import time
from starlette.concurrency import run_in_threadpool

router = APIRouter(prefix='/metadata', tags=['LOCATION_METADATA'])

@router.post('/extract_metadata')
async def extract_metadata(address : str, radius : str, project_id : str):
    """
    This function extracts the location metadata and stores it in database.
    """
    start_time = time.time()
    radius = int(radius)
    try:
        print(f"Coordinate Extraction started for input : {address} and radius: {radius}")
        src_lat, src_lng = extract_latitude_longitude(address=address)
        print(f"Coordinate Extraction Complete")


        print(f"AQI fetching")
        air_quality = aqi(src_lat,src_lng)
        print(f"AQI fetching completed")

        vicinity_map = {}
        vicinity_map['address'] = address
        vicinity_map['_id']=project_id
        vicinity_map['air_quality_index'] = air_quality

        print(f"Education area fetching")
        vicinity_map['education'] = []
        vicinity_map = educationDB(vicinity_map=vicinity_map, src_lat=src_lat, src_lng=src_lng, radius=radius)
        print(f"Education area fetching completed")

        print(f"healthcare area fetching")
        vicinity_map['healthcare']=[]
        vicinity_map = healthcareDB(vicinity_map=vicinity_map, src_lat=src_lat, src_lng=src_lng, radius=radius)
        print(f"healthcare area fetching completed")

        print(f"entertainment area fetching")
        vicinity_map['entertainment']=[]
        vicinity_map = entertainmentDB(vicinity_map=vicinity_map, src_lat=src_lat, src_lng=src_lng, radius=radius)
        print(f"entertainment area fetching completed")

        print(f"landmark area fetching")
        vicinity_map['landmark']=[]
        vicinity_map = landmarkDB(vicinity_map=vicinity_map, src_lat=src_lat, src_lng=src_lng, radius=radius)
        print(f"landmark area fetching completed")

        print(f"restaurant area fetching")
        vicinity_map['restaurant']=[]
        vicinity_map = restaurantDB(vicinity_map=vicinity_map, src_lat=src_lat, src_lng=src_lng, radius=radius)
        print(f"restaurant area fetching completed")

        print(f"shopping area fetching")
        vicinity_map['shopping']=[]
        vicinity_map = shoppingDB(vicinity_map=vicinity_map, src_lat=src_lat, src_lng=src_lng, radius=radius)
        print(f"shopping area fetching completed")


        # vicinity_map_list = []
        # vicinity_map_list.append(vicinity_map)

        print(f"Database instance")
        await run_in_threadpool(insert_metadata_to_db, vicinity_map=vicinity_map)
        print(f"Data generation completed successfully")

        return JSONResponse(status_code=200, content={'message': 'Data uploaded successfully', 'response_time': f'{round(time.time()-start_time,2)}s'})

    except Exception as e:
        print(f"Unable to upload location metadata: {e}")
        return JSONResponse(status_code=500, content={'message': f'Error uploading data: {e}', 'response_time': f'{round(time.time()-start_time,2)}s'})