from pydantic import BaseModel, Field, confloat
from typing import Literal


class CloudCover(BaseModel):
    afternoon: int = Field(..., description="Cloud cover at 12:00", ge=0, le=100)


class Humidity(BaseModel):
    afternoon: int = Field(..., description="Relative humidity at 12:00", ge=0, le=100)


class Precipitation(BaseModel):
    total: float = Field(..., description="Total amount of precipitation in mm", ge=0)


class Pressure(BaseModel):
    afternoon: int = Field(..., description="Atmospheric pressure at 12:00 in hPa")


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


class WeatherResponse(BaseModel):
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


class ErrorResponse(BaseModel):
    error: dict[str, str]