import requests


def get_weather(latitude, longitude):

    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": latitude,
        "longitude": longitude,

        "current": [
            "temperature_2m",
            "relative_humidity_2m",
            "wind_speed_10m"
        ],

        "daily": [
            "precipitation_probability_max"
        ],

        "timezone": "auto",
        "forecast_days": 1
    }

    response = requests.get(
        url,
        params=params,
        timeout=10
    )

    response.raise_for_status()

    data = response.json()

    return {
        "temperature":
            data["current"]["temperature_2m"],

        "humidity":
            data["current"]["relative_humidity_2m"],

        "wind_speed":
            data["current"]["wind_speed_10m"],

        "rain_probability":
            data["daily"]["precipitation_probability_max"][0]
    }