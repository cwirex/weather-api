from datetime import datetime, timedelta

# Sample cities data
SAMPLE_CITIES = {
    "london": {
        "name": "London",
        "country": "GB",
        "coordinates": {"lat": 51.5074, "lon": -0.1278}
    },
    "paris": {
        "name": "Paris",
        "country": "FR",
        "coordinates": {"lat": 48.8566, "lon": 2.3522}
    },
    "new york": {
        "name": "New York",
        "country": "US",
        "coordinates": {"lat": 40.7128, "lon": -74.0060}
    }
}

def generate_sample_weather(city_name: str, date: str, units: str) -> dict:
    """Generate sample weather data for testing purposes"""
    return {
        "city": SAMPLE_CITIES[city_name.lower()],
        "date": date,
        "weather": {
            "temperature": {
                "min": 12.5,
                "max": 18.5,
                "morning": 13.2,
                "day": 17.8,
                "evening": 15.5,
                "night": 12.8,
                "feels_like": {
                    "morning": 12.5,
                    "day": 17.2,
                    "evening": 15.0,
                    "night": 12.1
                }
            },
            "humidity": {
                "morning": 65,
                "day": 55,
                "evening": 60,
                "night": 70
            },
            "pressure": 1012,
            "wind": {
                "speed": 5.2,
                "direction": "NE"
            },
            "precipitation": {
                "probability": 30,
                "total": 0.5
            },
            "sun": {
                "sunrise": "07:15:00",
                "sunset": "16:45:00"
            },
            "summary": "Partly cloudy throughout the day with a chance of rain"
        },
        "meta": {
            "cached": True,
            "cache_time": datetime.utcnow().isoformat() + "Z",
            "provider": "OpenWeatherMap",
            "data_type": "current"
        }
    }

def get_sample_stats(city_name: str, start_date: str, end_date: str, units: str) -> dict:
    """Generate sample weather statistics"""
    return {
        "city": SAMPLE_CITIES[city_name.lower()],
        "period": {
            "start": start_date,
            "end": end_date
        },
        "temperature": {
            "min": 10.5,
            "max": 22.3,
            "average": 16.4
        },
        "precipitation": {
            "total": 45.2,
            "rainy_days": 8
        },
        "common_conditions": [
            {"condition": "Partly cloudy", "frequency": 45},
            {"condition": "Clear sky", "frequency": 30},
            {"condition": "Light rain", "frequency": 25}
        ],
        "meta": {
            "cached": True,
            "cache_time": datetime.utcnow().isoformat() + "Z"
        }
    }