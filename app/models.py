from pydantic import BaseModel, Field, confloat
from typing import Literal, Optional, Dict, Any


class CloudCover(BaseModel):
    afternoon: int = Field(..., description="Cloud cover at 12:00", ge=0, le=100)


class Humidity(BaseModel):
    afternoon: int = Field(..., description="Relative humidity at 12:00", ge=0, le=100)


class Precipitation(BaseModel):
    total: float = Field(..., description="Total amount of precipitation in mm", ge=0)


class Pressure(BaseModel):
    afternoon: float = Field(..., description="Atmospheric pressure at 12:00 in hPa")  # Changed from int to float


class Temperature(BaseModel):
    min: float = Field(..., description="Minimum temperature")
    max: float = Field(..., description="Maximum temperature")
    afternoon: float = Field(..., description="Temperature at 12:00")
    night: float = Field(..., description="Temperature at 00:00")
    evening: float = Field(..., description="Temperature at 18:00")
    morning: float = Field(..., description="Temperature at 06:00")


class WindMax(BaseModel):
    speed: float = Field(..., description="Maximum wind speed")
    direction: int = Field(..., description="Wind direction in degrees", ge=0, le=360)


class Wind(BaseModel):
    max: WindMax


class WeatherMeta(BaseModel):
    cached: bool = Field(..., description="Whether the response was served from cache")
    cache_time: Optional[str] = Field(None, description="Time when the data was cached")
    provider: str = Field("OpenMeteo", description="Weather data provider")  # Updated default provider
    data_type: str = Field(..., description="Type of data (current/historical/forecast/stats)")


class BaseWeatherResponse(BaseModel):
    lat: confloat(ge=-90, le=90) = Field(..., description="Latitude")
    lon: confloat(ge=-180, le=180) = Field(..., description="Longitude")
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    units: Literal["standard", "metric", "imperial"]
    cloud_cover: CloudCover
    humidity: Humidity
    precipitation: Precipitation
    temperature: Temperature
    pressure: Pressure
    wind: Wind


class WeatherResponse(BaseWeatherResponse):
    meta: Optional[WeatherMeta] = Field(None, description="Metadata about the response")


class TemperatureStats(BaseModel):
    min: float = Field(..., description="Minimum temperature in the period")
    max: float = Field(..., description="Maximum temperature in the period")
    average: float = Field(..., description="Average temperature in the period")


class PrecipitationStats(BaseModel):
    total: float = Field(..., description="Total precipitation in the period")
    days_with_precipitation: int = Field(..., description="Number of days with precipitation")


class WindStats(BaseModel):
    average_speed: float = Field(..., description="Average wind speed in the period")
    max_speed: float = Field(..., description="Maximum wind speed in the period")


class HumidityStats(BaseModel):
    average: float = Field(..., description="Average humidity in the period")
    min: int = Field(..., description="Minimum humidity in the period", ge=0, le=100)
    max: int = Field(..., description="Maximum humidity in the period", ge=0, le=100)


class WeatherStats(BaseModel):
    temperature: TemperatureStats
    precipitation: PrecipitationStats
    wind: WindStats
    humidity: HumidityStats
    meta: Optional[WeatherMeta] = Field(None, description="Metadata about the response")


class CacheStats(BaseModel):
    status: str = Field(..., description="Current status of the cache")
    total_keys: int = Field(..., description="Total number of keys in cache")
    memory_usage: str = Field(..., description="Memory usage of the cache")
    hit_rate: str = Field(..., description="Cache hit rate")
    miss_rate: str = Field(..., description="Cache miss rate")
    evicted_keys: int = Field(..., description="Number of keys evicted")
    expired_keys: int = Field(..., description="Number of keys expired")
    uptime: str = Field(..., description="Cache uptime")
    connected_clients: int = Field(..., description="Number of connected clients")
    last_save: str = Field(..., description="Last save timestamp")
    cache_type_distribution: Dict[str, int] = Field(..., description="Distribution of cache entries by type")


class CacheClearResponse(BaseModel):
    status: str = Field(..., description="Operation status")
    message: str = Field(..., description="Operation message")
    timestamp: str = Field(..., description="Operation timestamp")
    details: Dict[str, Any] = Field(..., description="Operation details")


class ErrorResponse(BaseModel):
    error: Dict[str, str]