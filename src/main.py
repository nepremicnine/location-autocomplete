from fastapi import FastAPI, HTTPException, Depends
from fastapi.routing import APIRouter
import os
from dotenv import load_dotenv
import httpx
import pybreaker
import re
import requests
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryError,
)

# Load environment variables from .env file
load_dotenv()

API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")
LOCATION_AUTOCOMPLETE_SERVER_MODE = os.getenv(
    "LOCATION_AUTOCOMPLETE_SERVER_MODE", "development"
)
LOCATION_AUTOCOMPLETE_SERVER_PORT = os.getenv("LOCATION_AUTOCOMPLETE_SERVER_PORT", 8080)

# Determine the prefix based on the server mode
API_PREFIX = (
    "/location-autocomplete" if LOCATION_AUTOCOMPLETE_SERVER_MODE == "release" else ""
)

app = FastAPI(
    title="Location Autocomplete API",
    description="API for getting location suggestions, geometry, and name based on Google Places API",
    version="1.0.0",
    openapi_url=f"{API_PREFIX}/openapi.json",
    docs_url=f"{API_PREFIX}/docs",
    redoc_url=f"{API_PREFIX}/redoc",
)

# Breaker Configuration
breaker = pybreaker.CircuitBreaker(fail_max=3, reset_timeout=30)


# Retry Configuration
def is_transient_error(exception):
    """Define what qualifies as a transient error."""
    return isinstance(exception, requests.exceptions.RequestException)


retry_strategy = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=6),
    retry=retry_if_exception_type(requests.exceptions.RequestException),
)


# Helper function with Circuit Breaker for getting suggestions
@retry_strategy
@breaker
async def get_suggestions_from_google(input: str):
    api_url = "https://maps.googleapis.com/maps/api/place/autocomplete/json"
    params = {"key": API_KEY, "sensor": "false", "input": input}

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

    return result


# Get location suggestion based on string input
@app.get(f"{API_PREFIX}/location/suggestions")
async def get_suggestions(input: str):
    try:
        result = await get_suggestions_from_google(input)
        return {"suggestions": result}

    except RetryError as retry_error:
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable after multiple retry attempts. Please try again later.",
        )

    except pybreaker.CircuitBreakerError:
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable due to repeated failures.",
        )

    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")

    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=response.status_code, detail=f"API error: {str(e)}"
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Helper function with Circuit Breaker for getting geometry
@retry_strategy
@breaker
async def get_geomtery_from_google(place_id: str):
    api_url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {"key": API_KEY, "fields": "geometry", "place_id": place_id}

    async with httpx.AsyncClient() as client:
        response = await client.get(api_url, params=params)

    response.raise_for_status()
    response_json = response.json()

    latitude = response_json["result"]["geometry"]["location"]["lat"]
    longitude = response_json["result"]["geometry"]["location"]["lng"]

    return latitude, longitude


# Get location latitude and longitude based on place_id
@app.get(f"{API_PREFIX}/location/geometry")
async def get_geometry(place_id: str):
    try:
        latitude, longitude = await get_geomtery_from_google(place_id)

        return {
            "latitude": latitude,
            "longitude": longitude,
            "geometry": f"POINT({longitude} {latitude})",
        }
    except RetryError as retry_error:
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable after multiple retry attempts. Please try again later.",
        )

    except pybreaker.CircuitBreakerError:
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable due to repeated failures.",
        )

    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")

    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=response.status_code, detail=f"API error: {str(e)}"
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Helper function with Circuit Breaker for getting geometry
@retry_strategy
@breaker
async def get_name_from_google(place_id: str):
    api_url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {"key": API_KEY, "place_id": place_id}

    async with httpx.AsyncClient() as client:
        response = await client.get(api_url, params=params)

    response.raise_for_status()
    response_json = response.json()

    name = response_json["result"]["formatted_address"]
    
    return name

# Get location name from place_id
@app.get(f"{API_PREFIX}/location/name")
async def get_name(place_id: str):
    try:
        name = await get_name_from_google(place_id)
        return {"name": name}
    
    except RetryError as retry_error:
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable after multiple retry attempts. Please try again later.",
        )

    except pybreaker.CircuitBreakerError:
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable due to repeated failures.",
        )
    
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")
    
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=response.status_code, detail=f"API error: {str(e)}"
        )
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Health check endpoint
@app.get(f"{API_PREFIX}/health")
async def health():
    return {"status": "ok"}
