# PR Weather

An app that tells you if the weather is going to be great for running a PR
  

# Why Does This Exist

Running a fast road race depends on a lot of things - training, nutrition, fueling, hills (those damn hills) - but another key factor is weather. Every bump in temperature above ~55F has significant effects on finishing time for endurance runners, not to mention humidity, rain, snow, or wind. So obsessive checking of race-day weather predictions is a regular tradition for runners looking to set their next PR. 

The only problem? There aren’t many great solutions for a running-focused weather prediction app that highlights the data most important to runners, alongside the general confidence of the weather prediction at that time. Welcome: PR Weather
  

# How Does it Work?

Since I don’t have the funds to install weather stations around the world, PR Weather grabs both historic and future weather data from open source Weather APIs, and displays them in a convenient format

Since weather predictions aren’t terribly accurate more than a few weeks out, historic weather data is used to get an idea of how the weather could be, based on how it was years in the past.
  

# Features

- Weather data for popular marathons throughout the US
- Forecasts for weather with relative prediction confidence
- Historic weather for the same location and day in past years
- Graph visualizing historic weather trends from multiple years for the duration of the race (e.g. 7am-11am on 4/19 2020-2025)
  

# Roadmap

- Frontend styling
- Clean up API processing logic
- Data ~~scraping~~ gathering with Scrapy
- Ethically borrow race information to improve coverage
- More unit tests
- Mapping integration
- Signup for daily forecast notifications via AWS SNS