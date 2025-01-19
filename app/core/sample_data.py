from datetime import datetime
from typing import Literal

# Comprehensive city data
CITIES = {
    "london,gb": {
        "name": "London",
        "country": "GB",
        "state": "England",
        "lat": 51.5074,
        "lon": -0.1278,
        "tz": "+00:00"
    },
    "paris,fr": {
        "name": "Paris",
        "country": "FR",
        "state": "Île-de-France",
        "lat": 48.8566,
        "lon": 2.3522,
        "tz": "+01:00"
    },
    "new york,us": {
        "name": "New York",
        "country": "US",
        "state": "New York",
        "lat": 40.7128,
        "lon": -74.0060,
        "tz": "-05:00"
    },
    "tokyo,jp": {
        "name": "Tokyo",
        "country": "JP",
        "state": "Tokyo",
        "lat": 35.6762,
        "lon": 139.6503,
        "tz": "+09:00"
    }
}


def convert_temperature(temp: float, units: str) -> float:
    """Convert temperature from Kelvin to specified units"""
    if units == "metric":
        return round(temp - 273.15, 2)  # Kelvin to Celsius
    elif units == "imperial":
        return round((temp - 273.15) * 9 / 5 + 32, 2)  # Kelvin to Fahrenheit
    return round(temp, 2)  # Standard (Kelvin)


def convert_wind_speed(speed: float, units: str) -> float:
    """Convert wind speed from m/s to specified units"""
    if units == "imperial":
        return round(speed * 2.237, 2)  # m/s to mph
    return round(speed, 2)  # metric and standard (m/s)


def generate_sample_weather(city_key: str, date: str, units: Literal["standard", "metric", "imperial"]) -> dict:
    """Generate sample weather data for testing purposes"""
    city_data = CITIES[city_key]

    # Base temperature in Kelvin
    base_temp = 293.15  # 20°C / 68°F
    temp_data = {
        "min": base_temp - 5,
        "max": base_temp + 5,
        "afternoon": base_temp + 3,
        "night": base_temp - 3,
        "evening": base_temp + 1,
        "morning": base_temp - 2
    }

    # Convert temperatures based on requested units
    converted_temp = {
        k: convert_temperature(v, units)
        for k, v in temp_data.items()
    }

    # Base wind speed in m/s
    base_wind_speed = 5.2

    return {
        "lat": city_data["lat"],
        "lon": city_data["lon"],
        "tz": city_data["tz"],
        "date": date,
        "units": units,
        "cloud_cover": {
            "afternoon": 45
        },
        "humidity": {
            "afternoon": 65
        },
        "precipitation": {
            "total": 0.5
        },
        "temperature": converted_temp,
        "pressure": {
            "afternoon": 1015
        },
        "wind": {
            "max": {
                "speed": convert_wind_speed(base_wind_speed, units),
                "direction": 120
            }
        }
    }


def get_sample_stats(
        city_key: str,
        start_date: str,
        end_date: str,
        units: Literal["standard", "metric", "imperial"]
) -> dict:
    """Generate sample weather statistics"""
    city_data = CITIES[city_key]
    base_temp = 293.15  # Base temperature in Kelvin

    stats = {
        "location": {
            "name": city_data["name"],
            "country": city_data["country"],
            "lat": city_data["lat"],
            "lon": city_data["lon"],
            "tz": city_data["tz"]
        },
        "period": {
            "start": start_date,
            "end": end_date
        },
        "temperature": {
            "min": convert_temperature(base_temp - 8, units),
            "max": convert_temperature(base_temp + 8, units),
            "average": convert_temperature(base_temp, units)
        },
        "precipitation": {
            "total": 45.2,
            "days_with_precipitation": 8
        },
        "wind": {
            "average_speed": convert_wind_speed(4.5, units),
            "max_speed": convert_wind_speed(12.3, units)
        },
        "humidity": {
            "average": 65,
            "min": 45,
            "max": 85
        }
    }

    return stats