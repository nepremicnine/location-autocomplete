from fastapi import FastAPI, HTTPException, Depends
from fastapi.routing import APIRouter
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
import httpx
import pybreaker
import requests
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryError,
)
from src.cpuhealth import check_cpu_health
from src.diskhealth import check_disk_health
from src.models import HealthResponse

# Load environment variables from .env file
load_dotenv()

API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")
LOCATION_AUTOCOMPLETE_SERVER_MODE = os.getenv(
    "LOCATION_AUTOCOMPLETE_SERVER_MODE", "development"
)
LOCATION_AUTOCOMPLETE_SERVER_PORT = os.getenv("LOCATION_AUTOCOMPLETE_SERVER_PORT", 8080)
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8080")

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


origins = [
    FRONTEND_URL,
    BACKEND_URL,
    "http://localhost",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


# Health check endpoint
@app.get(f"{API_PREFIX}/health/liveness")
async def liveness_check():
    return {"status": "ok"}


# Health check Google Places API
@app.get(f"{API_PREFIX}/health/google-places")
async def google_places_api_health_check():
    params = {
        "query": "test",
        "key": API_KEY,
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get('https://maps.googleapis.com/maps/api/place/textsearch/json', params=params)
            if response.status_code == 200 and "results" in response.json():
                return {"status": "ok"}
            else:
                return {
                    "status": "error",
                    "detail": "Unexpected response from Google Places API",
                }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


# Health check CPU
@app.get(f"{API_PREFIX}/health/cpu", response_model=HealthResponse)
async def cpu_health_check():
    cpu_health = check_cpu_health()
    return HealthResponse(status=cpu_health.status, components={"cpu": cpu_health})


# Health check memory
@app.get(f"{API_PREFIX}/health/disk", response_model=HealthResponse)
async def disk_health_check():
    disk_health = check_disk_health()
    return HealthResponse(status=disk_health.status, components={"disk": disk_health})


@app.get(f"{API_PREFIX}/health/readiness")
async def readiness_check():
    liveness = await liveness_check()
    google_places_health = await google_places_api_health_check()
    cpu_health = check_cpu_health()
    disk_health = check_disk_health()

    if liveness["status"] == "ok" and cpu_health.status == "UP" and disk_health.status == "UP" and google_places_health["status"] == "ok":
        return {"status": "ok"}
    else:
        return {"status": "error"}
