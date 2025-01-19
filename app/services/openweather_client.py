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
    HumidityStats
)


class OpenWeatherClient:
    def __init__(self, api_key: str, base_url: str = "https://api.openweathermap.org/data/3.0"):
        self.api_key = api_key
        self.base_url = base_url
        self._client: Optional[httpx.AsyncClient] = None

    @property
    async def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self):
        """Close the HTTP client"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _build_url(self, endpoint: str) -> str:
        return f"{self.base_url}/{endpoint}"

    async def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make request to OpenWeather API with error handling"""
        params["appid"] = self.api_key

        try:
            client = await self.client
            response = await client.get(
                self._build_url(endpoint),
                params=params
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail={
                        "code": "CITY_NOT_FOUND",
                        "message": "City not found in OpenWeather database",
                        "details": str(e)
                    }
                )
            elif e.response.status_code == 429:
                raise HTTPException(
                    status_code=429,
                    detail={
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "OpenWeather API rate limit exceeded",
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

    async def get_current_weather(
            self,
            lat: float,
            lon: float,
            units: Literal["standard", "metric", "imperial"] = "metric"
    ) -> WeatherResponse:
        """Get current weather data"""
        params = {
            "lat": lat,
            "lon": lon,
            "units": units
        }

        data = await self._make_request("weather", params)
        weather_data = self._transform_current_response(data)
        weather_data.meta = WeatherMeta(
            cached=False,
            cache_time=None,
            provider="OpenWeatherMap",
            data_type="current"
        )
        return weather_data

    async def get_historical_weather(
            self,
            lat: float,
            lon: float,
            date: str,
            units: Literal["standard", "metric", "imperial"] = "metric"
    ) -> WeatherResponse:
        """Get historical weather data"""
        dt = int(datetime.strptime(date, "%Y-%m-%d").timestamp())

        params = {
            "lat": lat,
            "lon": lon,
            "dt": dt,
            "units": units
        }

        data = await self._make_request("onecall/timemachine", params)
        weather_data = self._transform_historical_response(data)
        weather_data.meta = WeatherMeta(
            cached=False,
            cache_time=None,
            provider="OpenWeatherMap",
            data_type="historical"
        )
        return weather_data

    async def get_forecast(
            self,
            lat: float,
            lon: float,
            date: str,
            units: Literal["standard", "metric", "imperial"] = "metric"
    ) -> WeatherResponse:
        """Get weather forecast"""
        params = {
            "lat": lat,
            "lon": lon,
            "units": units,
            "exclude": "minutely,hourly"
        }

        data = await self._make_request("onecall", params)
        weather_data = self._transform_forecast_response(data, date)
        weather_data.meta = WeatherMeta(
            cached=False,
            cache_time=None,
            provider="OpenWeatherMap",
            data_type="forecast"
        )
        return weather_data

    async def get_weather_stats(
            self,
            lat: float,
            lon: float,
            start_date: str,
            end_date: str,
            units: Literal["standard", "metric", "imperial"] = "metric"
    ) -> WeatherStats:
        """Get weather statistics for a date range"""
        start_dt = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp())
        end_dt = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp())

        daily_data: List[Dict[str, Any]] = []
        current_dt = start_dt

        while current_dt <= end_dt:
            params = {
                "lat": lat,
                "lon": lon,
                "dt": current_dt,
                "units": units
            }
            data = await self._make_request("onecall/timemachine", params)
            daily_data.append(data)
            current_dt += 86400  # Add one day in seconds

        stats = self._calculate_statistics(daily_data, units)
        stats.meta = WeatherMeta(
            cached=False,
            cache_time=None,
            provider="OpenWeatherMap",
            data_type="stats"
        )
        return stats

    def _transform_current_response(self, data: Dict[str, Any]) -> WeatherResponse:
        """Transform OpenWeather current weather response to our format"""
        return WeatherResponse(
            lat=data["coord"]["lat"],
            lon=data["coord"]["lon"],
            date=datetime.utcfromtimestamp(data["dt"]).strftime("%Y-%m-%d"),
            units=data.get("units", "standard"),
            cloud_cover=CloudCover(
                afternoon=data["clouds"]["all"]
            ),
            humidity=Humidity(
                afternoon=data["main"]["humidity"]
            ),
            precipitation=Precipitation(
                total=data.get("rain", {}).get("1h", 0) + data.get("snow", {}).get("1h", 0)
            ),
            temperature=Temperature(
                min=data["main"]["temp_min"],
                max=data["main"]["temp_max"],
                afternoon=data["main"]["temp"],
                night=data["main"]["temp"],  # Current temp for night value
                evening=data["main"]["temp"],  # Current temp for evening value
                morning=data["main"]["temp"]  # Current temp for morning value
            ),
            pressure=Pressure(
                afternoon=data["main"]["pressure"]
            ),
            wind=Wind(
                max=WindMax(
                    speed=data["wind"]["speed"],
                    direction=data["wind"]["deg"]
                )
            )
        )

    def _transform_historical_response(self, data: Dict[str, Any]) -> WeatherResponse:
        """Transform OpenWeather historical response to our format"""
        return WeatherResponse(
            lat=data["lat"],
            lon=data["lon"],
            date=datetime.fromtimestamp(data["data"][0]["dt"]).strftime("%Y-%m-%d"),
            units=data.get("units", "standard"),
            cloud_cover=CloudCover(
                afternoon=data["data"][0]["clouds"]
            ),
            humidity=Humidity(
                afternoon=data["data"][0]["humidity"]
            ),
            precipitation=Precipitation(
                total=data["data"][0].get("rain", {}).get("1h", 0) + data["data"][0].get("snow", {}).get("1h", 0)
            ),
            temperature=Temperature(
                min=min(h["temp"] for h in data["data"]),
                max=max(h["temp"] for h in data["data"]),
                afternoon=next((h["temp"] for h in data["data"] if datetime.fromtimestamp(h["dt"]).hour == 12),
                               data["data"][0]["temp"]),
                night=next((h["temp"] for h in data["data"] if datetime.fromtimestamp(h["dt"]).hour == 0),
                           data["data"][0]["temp"]),
                evening=next((h["temp"] for h in data["data"] if datetime.fromtimestamp(h["dt"]).hour == 18),
                             data["data"][0]["temp"]),
                morning=next((h["temp"] for h in data["data"] if datetime.fromtimestamp(h["dt"]).hour == 6),
                             data["data"][0]["temp"])
            ),
            pressure=Pressure(
                afternoon=data["data"][0]["pressure"]
            ),
            wind=Wind(
                max=WindMax(
                    speed=max(h["wind_speed"] for h in data["data"]),
                    direction=data["data"][0]["wind_deg"]
                )
            )
        )

    def _transform_forecast_response(self, data: Dict[str, Any], target_date: str) -> WeatherResponse:
        """Transform OpenWeather forecast response to our format"""
        target_day = datetime.strptime(target_date, "%Y-%m-%d")

        # Find the forecast for the target date
        for daily in data["daily"]:
            if datetime.fromtimestamp(daily["dt"]).date() == target_day.date():
                return WeatherResponse(
                    lat=data["lat"],
                    lon=data["lon"],
                    date=target_date,
                    units=data.get("units", "standard"),
                    cloud_cover=CloudCover(
                        afternoon=daily["clouds"]
                    ),
                    humidity=Humidity(
                        afternoon=daily["humidity"]
                    ),
                    precipitation=Precipitation(
                        total=daily.get("rain", 0) + daily.get("snow", 0)
                    ),
                    temperature=Temperature(
                        min=daily["temp"]["min"],
                        max=daily["temp"]["max"],
                        afternoon=daily["temp"]["day"],
                        night=daily["temp"]["night"],
                        evening=daily["temp"]["eve"],
                        morning=daily["temp"]["morn"]
                    ),
                    pressure=Pressure(
                        afternoon=daily["pressure"]
                    ),
                    wind=Wind(
                        max=WindMax(
                            speed=daily["wind_speed"],
                            direction=daily["wind_deg"]
                        )
                    )
                )

        raise HTTPException(
            status_code=404,
            detail={
                "code": "FORECAST_NOT_AVAILABLE",
                "message": f"Forecast not available for {target_date}",
                "details": "Forecast data might not be available for the requested date"
            }
        )

    def _calculate_statistics(self, daily_data: List[Dict[str, Any]], units: str) -> WeatherStats:
        """Calculate statistics from daily weather data"""
        all_temps = []
        all_wind_speeds = []
        precipitation_days = 0
        total_precipitation = 0
        all_humidity = []

        for day in daily_data:
            for hour_data in day["data"]:
                all_temps.append(hour_data["temp"])
                all_wind_speeds.append(hour_data["wind_speed"])
                all_humidity.append(hour_data["humidity"])

                # Count precipitation
                precip = hour_data.get("rain", {}).get("1h", 0) + hour_data.get("snow", {}).get("1h", 0)
                if precip > 0:
                    precipitation_days += 1
                total_precipitation += precip

        return WeatherStats(
            temperature=TemperatureStats(
                min=min(all_temps),
                max=max(all_temps),
                average=sum(all_temps) / len(all_temps)
            ),
            precipitation=PrecipitationStats(
                total=total_precipitation,
                days_with_precipitation=precipitation_days // 24  # Convert hours to days
            ),
            wind=WindStats(
                average_speed=sum(all_wind_speeds) / len(all_wind_speeds),
                max_speed=max(all_wind_speeds)
            ),
            humidity=HumidityStats(
                average=sum(all_humidity) / len(all_humidity),
                min=min(all_humidity),
                max=max(all_humidity)
            )
        )