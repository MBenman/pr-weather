from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Avg
from collections import defaultdict
from .models import *
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.offline import plot
import plotly

def index(request):
    return HttpResponse("Hello, world. You're at the pr weather index.")


def race_weather(request, slug):
    race = get_object_or_404(Race, slug=slug)

    print(f"Race date: {race.date}")
    print(f"Race date (local): {timezone.localtime(race.date)}")

    race_date = race.date.date()

    weather_forecast = Weather.objects.filter(
        location=race.location,
        datetime__date=race_date
    ).order_by('datetime')

    historic_weather = Weather.objects.filter(
        location=race.location,
        datetime__month=race_date.month,
        datetime__day=race_date.day
    ).exclude(
        datetime__year=race_date.year
    ).order_by('datetime')

    location_weather_all = Weather.objects.filter(
        location=race.location,
    ).order_by('datetime')

    # If no forecast available, create from historic averages
    if not weather_forecast.exists():
        # Group historic weather by hour
        hourly_data = defaultdict(list)
        
        for weather in historic_weather:
            hour = weather.datetime.hour
            hourly_data[hour].append(weather)
        
        # Create forecast objects from averages
        forecast_objects = []
        for hour in range(24):  # 0-23 hours
            if hour in hourly_data:
                historic_for_hour = hourly_data[hour]
                
                # Calculate averages for this hour
                avg_temp = sum(w.temp for w in historic_for_hour if w.temp is not None) / len([w for w in historic_for_hour if w.temp is not None]) if any(w.temp is not None for w in historic_for_hour) else None
                avg_humidity = sum(w.humidity for w in historic_for_hour if w.humidity is not None) / len([w for w in historic_for_hour if w.humidity is not None]) if any(w.humidity is not None for w in historic_for_hour) else None
                avg_wind_speed = sum(w.wind_speed for w in historic_for_hour if w.wind_speed is not None) / len([w for w in historic_for_hour if w.wind_speed is not None]) if any(w.wind_speed is not None for w in historic_for_hour) else None
                # Add more fields as needed...
                
                # Create forecast datetime for this hour
                forecast_datetime = timezone.make_aware(
                    datetime.combine(race_date, datetime.min.time().replace(hour=hour))
                )
                
                # Create a Weather object (not saved to DB)
                forecast_weather = Weather(
                    location=race.location,
                    datetime=forecast_datetime,
                    temp=avg_temp,
                    humidity=avg_humidity,
                    wind_speed=avg_wind_speed,
                    # Add other fields...
                )
                forecast_objects.append(forecast_weather)
        
        weather_forecast = forecast_objects


#Can be removed
    print(f"All location weather: {location_weather_all.count()}")
    if location_weather_all:
        first = timezone.localtime(location_weather_all.first().datetime)
        last = timezone.localtime(location_weather_all.last().datetime)
        print(f"First record: {first}")
        print(f"Last record: {last}")
    
    print(f"Weather records found: {historic_weather.count()}")
    if historic_weather:
        first = timezone.localtime(historic_weather.first().datetime)
        last = timezone.localtime(historic_weather.last().datetime)
        print(f"First record: {first}")
        print(f"Last record: {last}")
#End can be removed

    # Convert to DataFrame
    if hasattr(weather_forecast, 'values'):
        # If it's a QuerySet
        wf_data = list(weather_forecast.values('datetime', 'temp', 'humidity', 'wind_speed', 'rain', 'precip_prob'))
    else:
        # If it's a list of Weather objects
        wf_data = []
        for weather in weather_forecast:
            wf_data.append({
                'datetime': weather.datetime,
                'temp': weather.temp,
                'humidity': weather.humidity,
                'wind_speed': weather.wind_speed,
                'rain': weather.rain,
                'precip_prob': weather.precip_prob,
            })
    
    wf_df = pd.DataFrame(wf_data)
    
    # Create Plotly graph if we have data
    forecast_graph = None
    if not wf_df.empty:
        # Convert datetime to local timezone for display
        wf_df['datetime_local'] = wf_df['datetime'].apply(lambda x: timezone.localtime(x))
        
        # Create the plot
        fig = go.Figure()
        
        # Add temperature line
        fig.add_trace(go.Scatter(
            x=wf_df['datetime_local'],
            y=wf_df['temp'],
            mode='lines+markers',
            name='Temperature (°F)',
            line=dict(color='red', width=2)
        ))
        
        # Add humidity on secondary y-axis
        fig.add_trace(go.Scatter(
            x=wf_df['datetime_local'],
            y=wf_df['humidity'],
            mode='lines+markers',
            name='Humidity (%)',
            yaxis='y2',
            line=dict(color='blue', width=2)
        ))
        
        # Update layout
        fig.update_layout(
            title=f'Weather Forecast for {race.name}',
            xaxis_title='Time',
            yaxis=dict(
                title='Temperature (°F)',
                title_font=dict(color='red'),
                tickfont=dict(color='red')
            ),
            yaxis2=dict(
                title='Humidity (%)',
                title_font=dict(color='blue'),
                tickfont=dict(color='blue'),
                anchor='x',
                overlaying='y',
                side='right'
            ),
            hovermode='x unified',
            template='plotly_white'
        )
        
        # Convert to HTML
        forecast_graph = plot(fig, output_type='div', include_plotlyjs=True)
    
    print(f"DataFrame shape: {wf_df.shape}")
    print(f"DataFrame columns: {wf_df.columns.tolist()}")
    

    return render(request, 'weatherapp/race.html', {
        'race': race,
        'weather_forecast': weather_forecast,
        'historic_weather': historic_weather,
        'forecast_graph': forecast_graph

    })