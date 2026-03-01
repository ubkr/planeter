"""In-memory cache service with TTL"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Any, Dict
from dataclasses import dataclass
import asyncio


@dataclass
class CacheEntry:
    """Cache entry with value and expiration time"""
    value: Any
    expires_at: datetime


class CacheService:
    """Simple in-memory cache with time-to-live (TTL)"""

    def __init__(self):
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache if not expired.

        Args:
            key: Cache key

        Returns:
            Cached value or None if expired/not found
        """
        async with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None

            # Check expiration
            if datetime.now(timezone.utc) > entry.expires_at:
                del self._cache[key]
                return None

            return entry.value

    async def set(self, key: str, value: Any, ttl_seconds: int):
        """
        Store value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time to live in seconds
        """
        async with self._lock:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
            self._cache[key] = CacheEntry(value=value, expires_at=expires_at)

    async def delete(self, key: str):
        """Delete a key from cache"""
        async with self._lock:
            self._cache.pop(key, None)

    async def clear(self):
        """Clear all cache entries"""
        async with self._lock:
            self._cache.clear()

    async def cleanup_expired(self):
        """Remove all expired entries from cache"""
        async with self._lock:
            now = datetime.now(timezone.utc)
            expired_keys = [
                key for key, entry in self._cache.items()
                if now > entry.expires_at
            ]
            for key in expired_keys:
                del self._cache[key]


# Global cache instance
cache = CacheService()
