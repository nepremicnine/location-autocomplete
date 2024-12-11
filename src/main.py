from fastapi import FastAPI, HTTPException, Depends
import os
from dotenv import load_dotenv 
import httpx

# Load environment variables from .env file
load_dotenv()

BASE_API_URL = os.getenv("API_URL")
API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")

app = FastAPI()

# Get location suggestion based on string input
@app.get("/location/suggestions")
async def get_suggestions(input: str):
    try:
        api_url = BASE_API_URL + '/autocomplete/json'
        params = {
            "key": API_KEY, 
            "sensor": "false", 
            "types": "(regions)", 
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
    
# Get location latitude and longitude based place_id
@app.get("/location/geometry")
async def get_geometry(place_id: str):
    try:
        api_url = BASE_API_URL + '/details/json'
        params = {
            "key": API_KEY, 
            "fields": "geometry", 
            "place_id": place_id
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, params=params)
        
        response.raise_for_status()
        responseJson = response.json()

        latitude = responseJson["result"]["geometry"]["location"]["lat"]
        longitude = responseJson["result"]["geometry"]["location"]["lng"]
        
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
    

