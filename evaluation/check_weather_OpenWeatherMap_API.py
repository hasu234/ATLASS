import sys
import subprocess
import pkg_resources

REQUIRED_PACKAGES = [
    'requests',  # Required for making HTTP requests
    'typing_extensions'
]

for package in REQUIRED_PACKAGES:
    try:
        dist = pkg_resources.get_distribution(package)
    except pkg_resources.DistributionNotFound:
        subprocess.call([sys.executable, '-m', 'pip', 'install', package])

from typing import Annotated, Dict, Any
import requests

Location = Annotated[str, "The location for which to retrieve weather data."]

WeatherData = Annotated[
    Dict[str, Any],
    "A dictionary containing current weather data such as temperature, humidity, wind speed, and weather conditions."
]

def get_current_weather(
    location: Location,
    api_key: Annotated[
        str,
        "The API key for authenticating with the OpenWeatherMap API."
    ]
) -> WeatherData:
    """
    Retrieve current weather data for a specified location using the OpenWeatherMap API.

    Args:
        location (Location): The location for which to retrieve weather data.
        api_key (str): The API key for the OpenWeatherMap API.

    Returns:
        WeatherData: A dictionary containing current weather data such as temperature, humidity, wind speed, and weather conditions.
    """
    url = "http://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": location,
        "appid": api_key,
        "units": "metric"  # Use metric units for temperature
    }

    # Make the request to the OpenWeatherMap API
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    # Extract relevant weather data
    weather_data = {
        "location": location,
        "temperature": data["main"]["temp"],
        "humidity": data["main"]["humidity"],
        "wind_speed": data["wind"]["speed"],
        "weather_conditions": data["weather"][0]["description"]
    }

    return weather_data

# Example call to the get_current_weather function
# Ensure to replace 'your_actual_api_key' with a valid OpenWeatherMap API key
api_key = "d1dd899b596c6343dee7893454537aa8"  # Replace with your actual API key
if api_key == "your_actual_api_key":
    print("Please replace 'your_actual_api_key' with a valid OpenWeatherMap API key.")
else:
    weather_info = get_current_weather(
        location="London",
        api_key=api_key
    )
    print(weather_info)

