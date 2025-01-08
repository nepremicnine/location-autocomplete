# from fastapi import FastAPI, HTTPException, Depends
# import os
# from dotenv import load_dotenv 
# import httpx

# # Load environment variables from .env file
# load_dotenv()

# API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")

# app = FastAPI()

# # Get location suggestion based on string input
# @app.get("/location/suggestions")
# async def get_suggestions(input: str):
#     try:
#         api_url = "https://maps.googleapis.com/maps/api/place/autocomplete/json"
#         params = {
#             "key": API_KEY, 
#             "sensor": "false", 
#             "input": input
#         }
        
#         async with httpx.AsyncClient() as client:
#             response = await client.get(api_url, params=params)
        
#         response.raise_for_status()
#         response_json = response.json()

#         # Extract description and place_id from predictions
#         predictions = response_json.get("predictions", [])
#         result = [
#             {"description": item["description"], "place_id": item["place_id"]}
#             for item in predictions
#         ]

#         return {
#             "suggestions": result
#         }
#     except httpx.RequestError as e:
#         raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")
#     except httpx.HTTPStatusError as e:
#         raise HTTPException(status_code=response.status_code, detail=f"API error: {str(e)}")
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))
    
# # Get location latitude and longitude based place_id
# @app.get("/location/geometry")
# async def get_geometry(place_id: str):
#     try:
#         api_url = "https://maps.googleapis.com/maps/api/place/details/json"
#         params = {
#             "key": API_KEY, 
#             "fields": "geometry", 
#             "place_id": place_id
#         }
        
#         async with httpx.AsyncClient() as client:
#             response = await client.get(api_url, params=params)
        
#         response.raise_for_status()
#         responseJson = response.json()

#         latitude = responseJson["result"]["geometry"]["location"]["lat"]
#         longitude = responseJson["result"]["geometry"]["location"]["lng"]
        
#         return {
#             "latitude": latitude,
#             "longitude": longitude,
#             "geometry": f"POINT({longitude} {latitude})"
#         }
#     except httpx.RequestError as e:
#         raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")
#     except httpx.HTTPStatusError as e:
#         raise HTTPException(status_code=response.status_code, detail=f"API error: {str(e)}")
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))
    
# # Get location name from place_id
# @app.get("/location/name")
# async def get_name(place_id: str):
#     try:
#         api_url = "https://maps.googleapis.com/maps/api/place/details/json"
#         params = {
#             "key": API_KEY, 
#             "place_id": place_id
#         }
        
#         async with httpx.AsyncClient() as client:
#             response = await client.get(api_url, params=params)
        
#         response.raise_for_status()
#         responseJson = response.json()

#         name = responseJson["result"]["formatted_address"]
        
#         return {
#             "name": name
#         }
#     except httpx.RequestError as e:
#         raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")
#     except httpx.HTTPStatusError as e:
#         raise HTTPException(status_code=response.status_code, detail=f"API error: {str(e)}")
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))
    

# # Health check endpoint
# @app.get("/health")
# async def health():
#     return {"status": "ok"}



from fastapi import FastAPI, HTTPException, Depends
from fastapi.routing import APIRouter
import os
from dotenv import load_dotenv
import httpx

# Load environment variables from .env file
load_dotenv()

API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")
LOCATION_AUTOCOMPLETE_SERVER_MODE = os.getenv("LOCATION_AUTOCOMPLETE_SERVER_MODE", "development")
LOCATION_AUTOCOMPLETE_SERVER_PORT = os.getenv("LOCATION_AUTOCOMPLETE_SERVER_PORT", 8080)

# Determine the prefix based on the server mode
API_PREFIX = "/location-autocomplete" if LOCATION_AUTOCOMPLETE_SERVER_MODE == "release" else ""

app = FastAPI(
    title="Location Autocomplete API",
    description="API for getting location suggestions, geometry, and name based on Google Places API",
    version="1.0.0",
    openapi_url=f"{API_PREFIX}/openapi.json",
    docs_url=f"{API_PREFIX}/docs",
    redoc_url=f"{API_PREFIX}/redoc",
)

# Get location suggestion based on string input
@app.get(f"{API_PREFIX}/location/suggestions")
async def get_suggestions(input: str):
    try:
        api_url = "https://maps.googleapis.com/maps/api/place/autocomplete/json"
        params = {
            "key": API_KEY,
            "sensor": "false",
            "input": input
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, params=params)
        
        response.raise_for_status()
        response_json = response.json()

        # Extract description and place_id from predictions
        predictions = response_json.get("predictions", [])
        result = [
            {"description": item["description"], "place_id": item["place_id"]}
            for item in predictions
        ]

        return {
            "suggestions": result
        }
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=response.status_code, detail=f"API error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
# Get location latitude and longitude based on place_id
@app.get(f"{API_PREFIX}/location/geometry")
async def get_geometry(place_id: str):
    try:
        api_url = "https://maps.googleapis.com/maps/api/place/details/json"
        params = {
            "key": API_KEY,
            "fields": "geometry",
            "place_id": place_id
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, params=params)
        
        response.raise_for_status()
        response_json = response.json()

        latitude = response_json["result"]["geometry"]["location"]["lat"]
        longitude = response_json["result"]["geometry"]["location"]["lng"]
        
        return {
            "latitude": latitude,
            "longitude": longitude,
            "geometry": f"POINT({longitude} {latitude})"
        }
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=response.status_code, detail=f"API error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
# Get location name from place_id
@app.get(f"{API_PREFIX}/location/name")
async def get_name(place_id: str):
    try:
        api_url = "https://maps.googleapis.com/maps/api/place/details/json"
        params = {
            "key": API_KEY,
            "place_id": place_id
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, params=params)
        
        response.raise_for_status()
        response_json = response.json()

        name = response_json["result"]["formatted_address"]
        
        return {
            "name": name
        }
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=response.status_code, detail=f"API error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    

# Health check endpoint
@app.get(f"{API_PREFIX}/health")
async def health():
    return {"status": "ok"}

