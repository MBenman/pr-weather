from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Race, Location, Weather
from . import services  # Import your services module


class LocationAdmin(admin.ModelAdmin):
    list_display = ['city', 'state', 'country', 'lat', 'long']
    actions = ['get_lat_long']

    def get_lat_long(self, request, queryset):
        success_count = 0
        error_count = 0
        
        for location in queryset:
            try:
                services.get_coord(location)  
                success_count += 1
            except Exception as e:
                error_count += 1
                messages.error(request, f"Error fetching coord for {location.city}: {str(e)}")
       
        if success_count:
            messages.success(request, f"Successfully fetched coords for {success_count} location(s)")
        if error_count:
            messages.error(request, f"Failed to fetch coords for {error_count} location(s)")
    
    get_lat_long.short_description = "Fetch coordinates for selected locations"

class RaceAdmin(admin.ModelAdmin):
    list_display = ['name', 'length', 'date', 'location']
    actions = ['fetch_weather_data', 'fetch_weather_forecast']

    def fetch_weather_data(self, request, queryset):
        success_count = 0
        error_count = 0

        for race in queryset:
            try:
                services.get_save_historic_weather(race)
                success_count += 1
            except Exception as e:
                error_count += 1
                messages.error(request, f"Error fetching weather for {race.name}: {str(e)}")

        if success_count:
            messages.success(request, f"Successfully fetched weather for {success_count} location(s)")
        if error_count:
            messages.error(request, f"Failed to fetch weather for {error_count} location(s)")
    
    fetch_weather_data.short_description = "Fetch weather for selected races"

    def fetch_weather_forecast(self, request, queryset):
        success_count = 0
        error_count = 0

        for race in queryset:
            try:
                services.get_save_forecast(race)
                success_count += 1
            except Exception as e:
                error_count += 1
                messages.error(request, f"Error fetching weather for {race.name}: {str(e)}")

        if success_count:
            messages.success(request, f"Successfully fetched weather for {success_count} location(s)")
        if error_count:
            messages.error(request, f"Failed to fetch weather for {error_count} location(s)")
    
    fetch_weather_forecast.short_description = "Fetch forecast for selected races"

admin.site.register(Location, LocationAdmin)
admin.site.register(Race, RaceAdmin)
admin.site.register(Weather)