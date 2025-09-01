import openmeteo_requests
import requests_cache
import numpy as np
from retry_requests import retry
from datetime import datetime, date, timedelta, timezone as dt_timezone
from django.utils import timezone
from collections import defaultdict
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

    # Use api to search for locations and coords based on city/state/country
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

    today = date.today()
    race_date = race.date.date()
    within_next_14_days = today < race_date <= today + timedelta(days=14)

    # Call the API to fetch weather if the race happnes within the next 14 days. Otherwise, generate weather data as an average of past weather
    if within_next_14_days:
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
            datetime.fromtimestamp(start_time + i * interval_seconds, tz=dt_timezone.utc)
            for i in range(int((end_time - start_time) / interval_seconds))
        ]

        # Get all variable values
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

    # Generate forecast from historic weather
    else:
        historic_weather = Weather.objects.filter(
            location=race.location,
            datetime__month=race_date.month,
            datetime__day=race_date.day
            ).exclude(
                datetime__year=race_date.year
            ).order_by('datetime')
        
        # Group historic weather by hour
        hourly_data = defaultdict(list)

    #    for w in historic_weather:
    #        print(f'Hour: {w.datetime.hour}')
    #        print(f'Temp: {w.temp}')
        
        for weather in historic_weather:
            hour = weather.datetime.hour
            hourly_data[hour].append(weather)
        
        for hour in range(24):  # 0-23 hours
            if hour in hourly_data:
                historic_for_hour = hourly_data[hour]
                
                # Helper function to calculate average
                def safe_avg(field_name):
                    values = [getattr(w, field_name) for w in historic_for_hour if getattr(w, field_name) is not None]
                    return sum(values) / len(values) if values else None
                
                # Calculate averages for this hour
                avg_temp = safe_avg('temp')
                avg_humidity = safe_avg('humidity')
                avg_rain = safe_avg('rain')
                avg_precip_prob = safe_avg('precip_prob')
                avg_precip = safe_avg('precip')
                avg_showers = safe_avg('showers')
                avg_snowfall = safe_avg('snowfall')
                avg_wind_speed = safe_avg('wind_speed')
                avg_wind_direction = safe_avg('wind_direction')
                avg_wind_gusts = safe_avg('wind_gusts')
                
                # Create forecast datetime for this hour
                forecast_datetime = timezone.make_aware(
                    datetime.combine(race_date, datetime.min.time().replace(hour=hour))
                )
                
                # Save the forecast weather to database
                Weather.objects.update_or_create(
                    location=race.location,
                    datetime=forecast_datetime,
                    defaults={
                        'temp': avg_temp,
                        'humidity': avg_humidity,
                        'rain': avg_rain,
                        'precip_prob': avg_precip_prob,
                        'precip': avg_precip,
                        'showers': avg_showers,
                        'snowfall': avg_snowfall,
                        'wind_speed': avg_wind_speed,
                        'wind_direction': avg_wind_direction,
                        'wind_gusts': avg_wind_gusts,
                    }
                )
        
        print(f"Generated forecast from historic data for {race_date}")
    

    

def get_save_historic_weather(race):

    lat = race.location.lat
    long = race.location.long
    race_date = race.date.date()
    start_year = 2022 # API history goes back to 2022
    end_year = race.date.year

    local_tz = timezone.get_current_timezone()

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
            "hourly": ["temperature_2m", "relative_humidity_2m", "rain", "precipitation_probability", "precipitation", "showers", "snowfall", "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m"],
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
                datetime.fromtimestamp(start_time + i * interval_seconds, tz=dt_timezone.utc)
                for i in range(int((end_time - start_time) / interval_seconds))
            ]


            # Get all variable values
            var_data = {
                "humidity": hourly.Variables(1).ValuesAsNumpy(),
                "temp": hourly.Variables(0).ValuesAsNumpy(),
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
