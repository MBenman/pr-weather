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

   # race_date = race.date.date()
   # race_time = race.date.time()
    race_local = timezone.localtime(race.date)
    race_date = race_local.date()
    race_time = race_local.time()

    print(f"Looking for: date={race_date}, hour={race_local.hour}")

    weather_forecast = Weather.objects.filter(
        location=race.location,
        datetime__date=race_date
    ).order_by('datetime')

    print(f"Weather forecast records found: {weather_forecast.count()}")

    # Debug: Show what hours are actually available
    if weather_forecast.exists():
        print("Available hours in weather data:")
        for w in weather_forecast:
            local_w = timezone.localtime(w.datetime)
            print(f"  {local_w} - Hour: {local_w.hour}")


    start_weather = Weather.objects.filter(
        location=race.location,
        datetime__date=race_date,
        datetime__hour=race_local.hour
    ).order_by('datetime')

    print(f"Start weather records found: {start_weather.count()}")



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
    
    print(f'race time: {race_time}')
    print(f'race local hour: {race_local.hour}')
    print(f'race hour: {race_time.hour}')
    
    

    return render(request, 'weatherapp/race.html', {
        'race': race,
        'weather_forecast': weather_forecast,
        'start_weather': start_weather,
        'historic_weather': historic_weather,
        'forecast_graph': forecast_graph

    })