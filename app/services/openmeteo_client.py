from datetime import datetime, timedelta
import httpx
from typing import Optional, Dict, Any, Literal, List
from fastapi import HTTPException
from app.models import (
    WeatherResponse,
    WeatherStats,
    WeatherMeta,
    CloudCover,
    Humidity,
    Precipitation,
    Temperature,
    Pressure,
    Wind,
    WindMax,
    TemperatureStats,
    PrecipitationStats,
    WindStats,
)

class OpenMeteoClient:
    def __init__(
            self,
            forecast_url: str = "https://api.open-meteo.com/v1/forecast",
            historical_url: str = "https://historical-forecast-api.open-meteo.com/v1/forecast"
    ):
        self.forecast_url = forecast_url
        self.historical_url = historical_url
        self._client: Optional[httpx.AsyncClient] = None

    def _convert_temperature(self, temp: float, to_units: str) -> float:
        """Convert temperature from Celsius (OpenMeteo default) to requested units"""
        if to_units == "standard":  # Convert Celsius to Kelvin
            return round(temp + 273.15, 2)
        elif to_units == "imperial":  # Convert Celsius to Fahrenheit
            return round((temp * 9/5) + 32, 2)
        return round(temp, 2)  # metric (Celsius)

    def _convert_wind_speed(self, speed: float, to_units: str) -> float:
        """Convert wind speed from km/h (OpenMeteo default) to requested units"""
        if to_units == "imperial":  # Convert km/h to mph
            return round(speed * 0.621371, 2)
        return round(speed, 2)  # metric and standard use m/s

    async def get_current_weather(
            self,
            lat: float,
            lon: float,
            units: Literal["standard", "metric", "imperial"] = "metric"
    ) -> WeatherResponse:
        """Get current weather data (and 7 days forecast)"""
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": [
                "temperature_2m",
                "relative_humidity_2m",
                "precipitation",
                "cloud_cover",
                "pressure_msl",
                "wind_speed_10m",
                "wind_direction_10m"
            ],
            "daily": [
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_sum",
                "wind_speed_10m_max",
                "wind_direction_10m_dominant"
            ],
            "timezone": "auto",
        }

        data = await self._make_request(self.forecast_url, params)

        # Extract current data
        current = data["current"]
        daily = data["daily"]

        # Convert values based on requested units
        temp = current["temperature_2m"]  # OpenMeteo returns in Celsius
        temp_min = daily["temperature_2m_min"][3]
        temp_max = daily["temperature_2m_max"][3]
        wind_speed = current["wind_speed_10m"]

        # Create response with converted values
        response = WeatherResponse(
            lat=lat,
            lon=lon,
            date=datetime.now().strftime("%Y-%m-%d"),
            units=units,  # Set the requested units
            cloud_cover=CloudCover(
                afternoon=current["cloud_cover"]
            ),
            humidity=Humidity(
                afternoon=current["relative_humidity_2m"]
            ),
            precipitation=Precipitation(
                total=current["precipitation"]
            ),
            temperature=Temperature(
                min=self._convert_temperature(temp_min, units),
                max=self._convert_temperature(temp_max, units),
                afternoon=self._convert_temperature(temp, units),
                night=self._convert_temperature(temp, units),
                evening=self._convert_temperature(temp, units),
                morning=self._convert_temperature(temp, units)
            ),
            pressure=Pressure(
                afternoon=current["pressure_msl"]
            ),
            wind=Wind(
                max=WindMax(
                    speed=self._convert_wind_speed(wind_speed, units),
                    direction=current["wind_direction_10m"]
                )
            )
        )

        return response

    async def get_historical_weather(
            self,
            lat: float,
            lon: float,
            date: str,
            units: Literal["standard", "metric", "imperial"] = "metric"
    ) -> WeatherResponse:
        """Get historical weather data"""
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": date,
            "end_date": date,
            "daily": [
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_sum",
                "wind_speed_10m_max",
                "wind_direction_10m_dominant"
            ],
            "timezone": "auto"
        }

        data = await self._make_request(self.historical_url, params)
        daily = data["daily"]

        # Convert values based on requested units
        temp_min = self._convert_temperature(daily["temperature_2m_min"][0], units)
        temp_max = self._convert_temperature(daily["temperature_2m_max"][0], units)
        temp_avg = (temp_min + temp_max) / 2
        wind_speed = self._convert_wind_speed(daily["wind_speed_10m_max"][0], units)

        return WeatherResponse(
            lat=lat,
            lon=lon,
            date=date,
            units=units,  # Set the requested units
            cloud_cover=CloudCover(
                afternoon=50  # Default value as historical data doesn't include cloud cover
            ),
            humidity=Humidity(
                afternoon=70  # Default value as historical data doesn't include humidity
            ),
            precipitation=Precipitation(
                total=daily["precipitation_sum"][0]
            ),
            temperature=Temperature(
                min=temp_min,
                max=temp_max,
                afternoon=temp_avg,  # Using average as actual time temps not available
                night=temp_min,  # Using min temp for night
                evening=temp_avg,  # Using average for evening
                morning=temp_avg  # Using average for morning
            ),
            pressure=Pressure(
                afternoon=1013  # Default value as historical data doesn't include pressure
            ),
            wind=Wind(
                max=WindMax(
                    speed=wind_speed,
                    direction=daily["wind_direction_10m_dominant"][0]
                )
            )
        )

    async def get_forecast(
            self,
            lat: float,
            lon: float,
            date: str,
            units: Literal["standard", "metric", "imperial"] = "metric"
    ) -> WeatherResponse:
        """Get weather forecast"""
        # Calculate days ahead
        target_date = datetime.strptime(date, "%Y-%m-%d")
        days_ahead = (target_date - datetime.now()).days

        if days_ahead > 7:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "FORECAST_NOT_AVAILABLE",
                    "message": "Forecast only available up to 7 days ahead",
                    "details": "OpenMeteo free tier limitation"
                }
            )

        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": [
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_sum",
                "wind_speed_10m_max",
                "wind_direction_10m_dominant"
            ],
            "timezone": "auto"
        }

        data = await self._make_request(self.forecast_url, params)
        daily = data["daily"]
        day_index = days_ahead

        # Convert values based on requested units
        temp_min = self._convert_temperature(daily["temperature_2m_min"][day_index], units)
        temp_max = self._convert_temperature(daily["temperature_2m_max"][day_index], units)
        temp_avg = (temp_min + temp_max) / 2
        wind_speed = self._convert_wind_speed(daily["wind_speed_10m_max"][day_index], units)

        return WeatherResponse(
            lat=lat,
            lon=lon,
            date=date,
            units=units,  # Set the requested units
            cloud_cover=CloudCover(
                afternoon=50  # Default value as forecast doesn't include hourly cloud cover
            ),
            humidity=Humidity(
                afternoon=70  # Default value as forecast doesn't include hourly humidity
            ),
            precipitation=Precipitation(
                total=daily["precipitation_sum"][day_index]
            ),
            temperature=Temperature(
                min=temp_min,
                max=temp_max,
                afternoon=temp_avg,  # Using average as actual time temps not available
                night=temp_min,  # Using min temp for night
                evening=temp_avg,  # Using average for evening
                morning=temp_avg  # Using average for morning
            ),
            pressure=Pressure(
                afternoon=1013  # Default value as forecast doesn't include pressure
            ),
            wind=Wind(
                max=WindMax(
                    speed=wind_speed,
                    direction=daily["wind_direction_10m_dominant"][day_index]
                )
            )
        )

    async def get_weather_stats(
            self,
            lat: float,
            lon: float,
            start_date: str,
            end_date: str,
            units: Literal["standard", "metric", "imperial"] = "metric"
    ) -> WeatherStats:
        """Get weather statistics for a date range"""
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": start_date,
            "end_date": end_date,
            "daily": [
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_sum",
                "wind_speed_10m_max"
            ],
            "timezone": "auto"
        }

        data = await self._make_request(self.historical_url, params)
        daily = data["daily"]

        # Calculate temperature statistics
        temp_min = min(daily["temperature_2m_min"])
        temp_max = max(daily["temperature_2m_max"])
        temp_avg = (sum(daily["temperature_2m_min"]) + sum(daily["temperature_2m_max"])) / (len(daily["temperature_2m_min"]) * 2)

        # Convert temperature values to requested units
        temp_min = self._convert_temperature(temp_min, units)
        temp_max = self._convert_temperature(temp_max, units)
        temp_avg = self._convert_temperature(temp_avg, units)

        # Calculate wind statistics
        wind_speeds = daily["wind_speed_10m_max"]
        max_wind = max(wind_speeds)
        avg_wind = sum(wind_speeds) / len(wind_speeds)

        # Convert wind speeds to requested units
        max_wind = self._convert_wind_speed(max_wind, units)
        avg_wind = self._convert_wind_speed(avg_wind, units)

        # Calculate precipitation statistics
        precip_values = daily["precipitation_sum"]
        total_precip = sum(precip_values)
        days_with_precip = sum(1 for p in precip_values if p > 0)

        return WeatherStats(
            temperature=TemperatureStats(
                min=temp_min,
                max=temp_max,
                average=temp_avg
            ),
            precipitation=PrecipitationStats(
                total=total_precip,
                days_with_precipitation=days_with_precip
            ),
            wind=WindStats(
                average_speed=avg_wind,
                max_speed=max_wind
            ),
        )

    async def close(self):
        """Close the HTTP client"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    @property
    async def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def _make_request(self, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make request to OpenMeteo API with error handling"""
        try:
            client = await self.client
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail={
                        "code": "LOCATION_NOT_FOUND",
                        "message": "Location not found in OpenMeteo database",
                        "details": str(e)
                    }
                )
            raise HTTPException(
                status_code=500,
                detail={
                    "code": "WEATHER_API_ERROR",
                    "message": "Error fetching weather data",
                    "details": str(e)
                }
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=500,
                detail={
                    "code": "WEATHER_API_ERROR",
                    "message": "Error connecting to weather service",
                    "details": str(e)
                }
            )