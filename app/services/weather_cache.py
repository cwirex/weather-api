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
    CacheClearResponse
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
            return 30 * 60  # 30 minutes

        if data_type == "forecast":
            if date:
                days_ahead = (
                        datetime.strptime(date, "%Y-%m-%d").date() -
                        datetime.now().date()
                ).days
                if days_ahead <= 5:
                    return 3 * 60 * 60  # 3 hours
                return 12 * 60 * 60  # 12 hours
            return 3 * 60 * 60  # Default to 3 hours

        if data_type == "historical":
            return 7 * 24 * 60 * 60  # 7 days

        if data_type == "stats":
            return 24 * 60 * 60  # 24 hours

        return 60 * 60  # Default 1 hour

    async def get(
            self,
            city: str,
            date: str,
            data_type: str
    ) -> Optional[Union[WeatherResponse, WeatherStats]]:
        """Get weather data from cache"""
        redis = await self.get_redis()
        key = self._get_key(city, date, data_type)

        data = await redis.get(key)
        if data:
            try:
                json_data = json.loads(data)

                # Add cache metadata
                meta = WeatherMeta(
                    cached=True,
                    cache_time=datetime.now().isoformat() + "Z",
                    provider="OpenWeatherMap",
                    data_type=data_type
                )

                if data_type == "stats":
                    stats = WeatherStats.model_validate(json_data)
                    stats.meta = meta
                    return stats
                else:
                    weather = WeatherResponse.model_validate(json_data)
                    weather.meta = meta
                    return weather

            except json.JSONDecodeError:
                await redis.delete(key)
                return None
            except ValueError as e:
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
        """Store weather data in cache"""
        redis = await self.get_redis()
        key = self._get_key(city, date, data_type)
        ttl = self._get_ttl(data_type, date)

        # Remove meta information before caching
        data_dict = data.model_dump()
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
            "current_weather": "weather:*:current",
            "historical": "weather:*:historical:*",
            "forecast": "weather:*:forecast:*"
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