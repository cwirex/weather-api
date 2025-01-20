from datetime import datetime, timedelta
import json
from typing import Optional, Dict, Any, Union
from redis.asyncio import Redis, ConnectionPool
from fastapi import HTTPException
from app.models import (
    WeatherResponse,
    WeatherStats,
    WeatherMeta,
    CacheStats,
    CacheClearResponse,
    Wind,
    WindMax,
    Temperature
)


class WeatherCache:
    def __init__(
            self,
            redis_host: str,
            redis_port: int,
            redis_db: int = 0,
            redis_password: Optional[str] = None
    ):
        self.pool = ConnectionPool(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            decode_responses=True
        )
        self._redis: Optional[Redis] = None

    async def get_redis(self) -> Redis:
        """Get Redis connection from pool"""
        if self._redis is None or self._redis.connection is None:
            self._redis = Redis(connection_pool=self.pool)
        return self._redis

    async def close(self):
        """Close Redis connection"""
        if self._redis:
            await self._redis.close()
            self._redis = None

    def _get_key(self, city: str, date: str, data_type: str) -> str:
        """Generate Redis key"""
        return f"weather:{city}:{date}:{data_type}"

    def _get_ttl(self, data_type: str, date: Optional[str] = None) -> int:
        """Get TTL in seconds based on data type and date"""
        if data_type == "current":
            return 15 * 60  # 15 minutes (OpenMeteo updates every ~15 mins)

        if data_type == "forecast":
            if date:
                days_ahead = (
                        datetime.strptime(date, "%Y-%m-%d").date() -
                        datetime.now().date()
                ).days
                if days_ahead <= 3:
                    return 2 * 60 * 60  # 2 hours for near-term forecast
                return 4 * 60 * 60  # 4 hours for extended forecast
            return 2 * 60 * 60  # Default to 2 hours

        if data_type == "historical":
            return 24 * 60 * 60  # 24 hours (historical data doesn't change often)

        if data_type == "stats":
            return 24 * 60 * 60  # 24 hours

        return 60 * 60  # Default 1 hour

    def _convert_temperature(self, temp: float, from_units: str, to_units: str) -> float:
        """Convert temperature between units"""
        # First convert to Kelvin if not already
        if from_units == "metric":
            kelvin = temp + 273.15
        elif from_units == "imperial":
            kelvin = (temp - 32) * 5 / 9 + 273.15
        else:  # standard (Kelvin)
            kelvin = temp

        # Then convert from Kelvin to target units
        if to_units == "metric":
            return round(kelvin - 273.15, 2)
        elif to_units == "imperial":
            return round((kelvin - 273.15) * 9 / 5 + 32, 2)
        return round(kelvin, 2)  # standard (Kelvin)

    def _convert_wind_speed(self, speed: float, from_units: str, to_units: str) -> float:
        """Convert wind speed between units"""
        # First convert to m/s if not already
        if from_units == "imperial":
            ms = speed / 2.237  # mph to m/s
        else:
            ms = speed  # both metric and standard use m/s

        # Then convert to target units
        if to_units == "imperial":
            return round(ms * 2.237, 2)  # m/s to mph
        return round(ms, 2)  # both metric and standard use m/s

    def _convert_units(
            self,
            data: Union[WeatherResponse, WeatherStats],
            from_units: str,
            to_units: str
    ) -> Union[WeatherResponse, WeatherStats]:
        """Convert all unit-dependent values in the weather data"""
        if from_units == to_units:
            return data

        if isinstance(data, WeatherResponse):
            # Convert temperatures
            old_temp = data.temperature
            data.temperature = Temperature(
                min=self._convert_temperature(old_temp.min, from_units, to_units),
                max=self._convert_temperature(old_temp.max, from_units, to_units),
                afternoon=self._convert_temperature(old_temp.afternoon, from_units, to_units),
                night=self._convert_temperature(old_temp.night, from_units, to_units),
                evening=self._convert_temperature(old_temp.evening, from_units, to_units),
                morning=self._convert_temperature(old_temp.morning, from_units, to_units)
            )

            # Convert wind speed
            old_wind = data.wind.max
            data.wind = Wind(
                max=WindMax(
                    speed=self._convert_wind_speed(old_wind.speed, from_units, to_units),
                    direction=old_wind.direction
                )
            )

            data.units = to_units

        elif isinstance(data, WeatherStats):
            # Convert temperature stats
            old_temp = data.temperature
            data.temperature.min = self._convert_temperature(old_temp.min, from_units, to_units)
            data.temperature.max = self._convert_temperature(old_temp.max, from_units, to_units)
            data.temperature.average = self._convert_temperature(old_temp.average, from_units, to_units)

            # Convert wind stats
            old_wind = data.wind
            data.wind.average_speed = self._convert_wind_speed(old_wind.average_speed, from_units, to_units)
            data.wind.max_speed = self._convert_wind_speed(old_wind.max_speed, from_units, to_units)

        return data

    async def get(
            self,
            city: str,
            date: str,
            data_type: str,
            units: str = "metric"
    ) -> Optional[Union[WeatherResponse, WeatherStats]]:
        """Get weather data from cache and convert to requested units"""
        redis = await self.get_redis()
        key = self._get_key(city, date, data_type)

        data = await redis.get(key)
        if data:
            try:
                json_data = json.loads(data)
                cached_units = json_data.get("units", "standard")

                # Add cache metadata
                meta = WeatherMeta(
                    cached=True,
                    cache_time=datetime.now().isoformat() + "Z",
                    provider="OpenMeteo",
                    data_type=data_type
                )

                if data_type == "stats":
                    stats = WeatherStats.model_validate(json_data)
                    stats.meta = meta
                    return self._convert_units(stats, cached_units, units)
                else:
                    weather = WeatherResponse.model_validate(json_data)
                    weather.meta = meta
                    return self._convert_units(weather, cached_units, units)

            except json.JSONDecodeError:
                await redis.delete(key)
                return None
            except ValueError:
                # Handle Pydantic validation errors
                await redis.delete(key)
                return None
        return None

    async def set(
            self,
            city: str,
            date: str,
            data_type: str,
            data: Union[WeatherResponse, WeatherStats]
    ) -> None:
        """Store weather data in cache (always in standard units)"""
        redis = await self.get_redis()
        key = self._get_key(city, date, data_type)
        ttl = self._get_ttl(data_type, date)

        # Create a copy for caching
        cache_data = data.model_copy(deep=True)

        # Convert copy to standard units before caching
        if cache_data.units != "standard":
            cache_data = self._convert_units(cache_data, cache_data.units, "standard")

        # Remove meta information before caching
        data_dict = cache_data.model_dump()
        data_dict.pop("meta", None)

        await redis.set(
            key,
            json.dumps(data_dict),
            ex=ttl
        )

    async def clear_city_cache(self, city: str) -> CacheClearResponse:
        """Clear all cached data for a city"""
        redis = await self.get_redis()
        pattern = f"weather:{city}:*"

        # Get all keys matching the pattern
        keys = []
        async for key in redis.scan_iter(pattern):
            keys.append(key)

        if not keys:
            return CacheClearResponse(
                status="success",
                message=f"No cache entries found for city: {city}",
                timestamp=datetime.utcnow().isoformat() + "Z",
                details={
                    "keys_removed": 0,
                    "memory_freed": "0 MB"
                }
            )

        # Get memory usage before deletion
        total_memory = 0
        for key in keys:
            memory = await redis.memory_usage(key)
            total_memory += memory or 0

        # Delete all keys
        await redis.delete(*keys)

        return CacheClearResponse(
            status="success",
            message=f"Cache cleared for city: {city}",
            timestamp=datetime.utcnow().isoformat() + "Z",
            details={
                "keys_removed": len(keys),
                "memory_freed": f"{total_memory / 1024 / 1024:.2f} MB"
            }
        )

    async def get_stats(self) -> CacheStats:
        """Get cache statistics"""
        redis = await self.get_redis()
        info = await redis.info()

        # Count keys by type
        patterns = {
            "current_weather": "weather:*:*:current",  # Matches weather:{city}:{date}:current
            "historical": "weather:*:*:historical",  # Matches weather:{city}:{date}:historical
            "forecast": "weather:*:*:forecast",  # Matches weather:{city}:{date}:forecast
            "stats": "weather:*:*:stats"  # Matches weather:{city}:{date}:stats
        }

        type_distribution = {}
        for data_type, pattern in patterns.items():
            count = 0
            async for _ in redis.scan_iter(pattern):
                count += 1
            type_distribution[data_type] = count

        return CacheStats(
            status="operational",
            total_keys=sum(type_distribution.values()),
            memory_usage=f"{info['used_memory'] / 1024 / 1024:.1f} MB",
            hit_rate=f"{info.get('keyspace_hits', 0) / (info.get('keyspace_hits', 0) + info.get('keyspace_misses', 1)) * 100:.1f}%",
            miss_rate=f"{info.get('keyspace_misses', 0) / (info.get('keyspace_hits', 0) + info.get('keyspace_misses', 1)) * 100:.1f}%",
            evicted_keys=info.get('evicted_keys', 0),
            expired_keys=info.get('expired_keys', 0),
            uptime=f"{info.get('uptime_in_days', 0)}d {info.get('uptime_in_seconds', 0) % (24 * 3600) // 3600}h {(info.get('uptime_in_seconds', 0) % 3600) // 60}m",
            connected_clients=info.get('connected_clients', 0),
            last_save=datetime.fromtimestamp(info.get('rdb_last_save_time', 0)).isoformat() + "Z",
            cache_type_distribution=type_distribution
        )