import openmeteo_requests
import requests_cache
import numpy as np
from retry_requests import retry
from datetime import datetime, timezone, date
import os
import sys

# Add the project root to the path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'weathersite.settings')
import django

from weatherapp.models import Weather, Location



def get_coord(location):

    city = location.city
    state = location.state
    country = location.country

    cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
    retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
    
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {
	"name": city,
	"count": 3,
    "format": "json"
    }

    response = retry_session.get(url, params=params)
    data = response.json()

    if "results" not in data or not data["results"]:
        raise ValueError(f"No results found for: {city}, {state}, {country}")
    
    # Normalize filters for matching
    def normalize(s):
        return s.strip().lower() if s else None

    target_country = normalize(country)
    target_state = normalize(state)

    # Filter by country and state (admin1), if provided
    filtered_results = []
    for result in data["results"]:
        result_country = normalize(result.get("country"))
        result_state = normalize(result.get("admin1"))

        if target_country and result_country != target_country:
            continue
        if target_state and result_state != target_state:
            continue

        filtered_results.append(result)

    if not filtered_results:
        raise ValueError(f"No results found for city='{city}' with state='{state}' and country='{country}'")

    best_match = filtered_results[0]  # implement ranking logic 

    print(best_match["latitude"], best_match["longitude"])

    location.lat = best_match["latitude"]
    location.long = best_match["longitude"] 
    location.save()  
    print(f"Updated {location} with coordinates: {location.lat}, {location.long}")

    return best_match["latitude"], best_match["longitude"]
    

def get_save_forecast(race):
    lat = race.location.lat
    long = race.location.long
    race_date = race.date.date()

    cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
    retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
    openmeteo = openmeteo_requests.Client(session = retry_session)
    url = "https://api.open-meteo.com/v1/forecast"

    params = {
            "latitude": lat,
            "longitude": long,
            "start_date": race_date,
            "end_date": race_date,
            "hourly": ["relative_humidity_2m", "temperature_2m", "rain", "precipitation_probability", "precipitation", "showers", "snowfall", "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m"],
            "wind_speed_unit": "mph",
            "temperature_unit": "fahrenheit"
            }
    responses = openmeteo.weather_api(url, params=params)
    response = responses[0]
    hourly = response.Hourly()
            
    start_time = hourly.Time()        # start timestamp (UNIX)
    end_time = hourly.TimeEnd()       # end timestamp (UNIX)
    interval_seconds = hourly.Interval()  

    # Generate list of timestamps
    times = [
        datetime.fromtimestamp(start_time + i * interval_seconds, tz=timezone.utc)
        for i in range(int((end_time - start_time) / interval_seconds))
    ]

    # Now get all variable values
    var_data = {
        "temp": hourly.Variables(0).ValuesAsNumpy(),
        "humidity": hourly.Variables(1).ValuesAsNumpy(),
        "rain": hourly.Variables(2).ValuesAsNumpy(),
        "precip_prob": hourly.Variables(3).ValuesAsNumpy(),
        "precip": hourly.Variables(4).ValuesAsNumpy(),
        "showers": hourly.Variables(5).ValuesAsNumpy(),
        "snowfall": hourly.Variables(6).ValuesAsNumpy(),
        "wind_speed": hourly.Variables(7).ValuesAsNumpy(),
        "wind_direction": hourly.Variables(8).ValuesAsNumpy(),
        "wind_gusts": hourly.Variables(9).ValuesAsNumpy()
    }
    
    
    print(f"Processing {len(times)} hours for {race_date}")
    location = race.location


    for i, dt in enumerate(times):
        weather_data = {
            field: float(var_data[field][i]) if not np.isnan(var_data[field][i]) else None
            for field in var_data
        }

        Weather.objects.update_or_create(
            location=location,
            datetime=dt,
            defaults=weather_data
        )

def get_save_historic_weather(race):

    lat = race.location.lat
    long = race.location.long
    race_date = race.date.date()
    start_year = 2022
    end_year = race.date.year

    # Setup the Open-Meteo API client with cache and retry on error
    cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
    retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
    openmeteo = openmeteo_requests.Client(session = retry_session)
    url = "https://historical-forecast-api.open-meteo.com/v1/forecast"

    for year in range(start_year, end_year + 1):
        try:
            current_date = race_date.replace(year=year)

            print(f"Fetching weather for {current_date}")

            params = {
            "latitude": lat,
            "longitude": long,
            "start_date": current_date,
            "end_date": current_date,
            "hourly": ["relative_humidity_2m", "temperature_2m", "rain", "precipitation_probability", "precipitation", "showers", "snowfall", "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m"],
            "wind_speed_unit": "mph",
            "temperature_unit": "fahrenheit"
            }

            responses = openmeteo.weather_api(url, params=params)

            response = responses[0]
            
            hourly = response.Hourly()
            
            start_time = hourly.Time()        # start timestamp (UNIX)
            end_time = hourly.TimeEnd()       # end timestamp (UNIX)
            interval_seconds = hourly.Interval()  

            # Generate list of timestamps
            times = [
                datetime.fromtimestamp(start_time + i * interval_seconds, tz=timezone.utc)
                for i in range(int((end_time - start_time) / interval_seconds))
            ]


            # Now get all variable values
            var_data = {
                "temp": hourly.Variables(0).ValuesAsNumpy(),
                "humidity": hourly.Variables(1).ValuesAsNumpy(),
                "rain": hourly.Variables(2).ValuesAsNumpy(),
                "precip_prob": hourly.Variables(3).ValuesAsNumpy(),
                "precip": hourly.Variables(4).ValuesAsNumpy(),
                "showers": hourly.Variables(5).ValuesAsNumpy(),
                "snowfall": hourly.Variables(6).ValuesAsNumpy(),
                "wind_speed": hourly.Variables(7).ValuesAsNumpy(),
                "wind_direction": hourly.Variables(8).ValuesAsNumpy(),
                "wind_gusts": hourly.Variables(9).ValuesAsNumpy()
            }
            
            


        # location, _ = Location.objects.get_or_create(lat=lat, long=long)
            print(f"Processing {len(times)} hours for {current_date}")
            location = race.location


            for i, dt in enumerate(times):
                weather_data = {
                    field: float(var_data[field][i]) if not np.isnan(var_data[field][i]) else None
                    for field in var_data
                }

                Weather.objects.update_or_create(
                    location=location,
                    datetime=dt,
                    defaults=weather_data
                )
        except Exception as e:
            print(f"Error fetching weather for {year}: {str(e)}")
            continue 
    print(f"Completed weather fetching from {start_year} to {end_year}")



    #return weather?
