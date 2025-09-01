from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.utils import timezone
from datetime import datetime, timedelta, timezone as dt_timezone 
from django.db.models import Avg
from collections import defaultdict
from .models import *
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.offline import plot
import plotly

def index(request):
    races = Race.objects.all()

    return render(request, 'weatherapp/index.html', {
        'races': races,
    })


def race_weather(request, slug):
    race = get_object_or_404(Race, slug=slug)

    print(f"Race date: {race.date}")
    print(f"Race date (local): {timezone.localtime(race.date)}")

   # race_date = race.date.date()
   # race_time = race.date.time()
   # race_local = timezone.localtime(race.date)
   # race_date = race_local.date()
   # race_time = race_local.time()

    # Convert race time to UTC to match how Django stores datetime
    race_utc = race.date.astimezone(dt_timezone.utc)
    race_date_utc = race_utc.date()
    race_hour_utc = race_utc.hour

    print(f"Race local: {race.date}")
    print(f"Race UTC: {race_utc} (date: {race_date_utc}, hour: {race_hour_utc})")   

    weather_forecast = Weather.objects.filter(
        location=race.location,
        datetime__date=race_date_utc
    ).order_by('datetime')

    print(f"Weather forecast records found: {weather_forecast.count()}")


    start_weather = Weather.objects.filter(
        location=race.location,
        datetime__date=race_date_utc,
        datetime__hour=race_hour_utc
    ).order_by('datetime')


    historic_weather = Weather.objects.filter(
        location=race.location,
        datetime__month=race_date_utc.month,
        datetime__day=race_date_utc.day
    ).exclude(
        datetime__year=race_date_utc.year
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
    
    
    

    return render(request, 'weatherapp/race.html', {
        'race': race,
        'weather_forecast': weather_forecast,
        'start_weather': start_weather,
        'historic_weather': historic_weather,
        'forecast_graph': forecast_graph

    })