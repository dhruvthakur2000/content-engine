import hashlib
import json
import os
import time
from typing import Optional, Dict

from backend.config.settings import get_settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class CacheManager:
    """
    Deterministic disk-based cache for expensive LLM node calls.

    Key features:
    - Content-addressable cache using SHA-256
    - Node-aware cache keys
    - TTL-based expiration
    - Disk persistence
    - Safe failure handling
    """

    def __init__(self):
        self.settings = get_settings()
        self.cache_dir = self.settings.cache_dir

        os.makedirs(self.cache_dir, exist_ok=True)

        logger.info(
            "cache_manager_initialized",
            cache_dir=self.cache_dir,
            ttl_hours=self.settings.cache_ttl_hours,
            enabled=self.settings.cache_enabled,
        )

    # ---------------------------------------------------------
    # HASHING
    # ---------------------------------------------------------

    def _hash_input(self, data: str, node_name: str) -> str:
        """
        Generates node-aware+ prompt version aware SHA256 cache key.
        Prevents collisions between different nodes.
        """
        prompt_version = self.settings.prompt_version
        
        normalized = data.strip()
        
        key = f"{prompt_version}:{node_name}:{normalized}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def _get_cache_path(self, cache_key: str) -> str:
        return os.path.join(self.cache_dir, f"{cache_key}.json")

    # ---------------------------------------------------------
    # READ CACHE
    # ---------------------------------------------------------

    def read(self, input_data: str, node_name: str) -> Optional[Dict]:

        if not self.settings.cache_enabled:
            return None 

        cache_key = self._hash_input(input_data, node_name)
        cache_path = self._get_cache_path(cache_key)

        if not os.path.exists(cache_path):
            logger.info("cache_miss", node=node_name, reason="file_not_found")
            return None

        file_age_seconds = time.time() - os.path.getmtime(cache_path)
        ttl_seconds = self.settings.cache_ttl_hours * 3600

        if file_age_seconds > ttl_seconds:
            logger.info(
                "cache_miss",
                node=node_name,
                reason="ttl_expired",
                age_hours=round(file_age_seconds / 3600, 1),
            )
            return None

        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached = json.load(f)

            logger.info(
                "cache_hit",
                node=node_name,
                age_hours=round(file_age_seconds / 3600, 1),
            )

            return cached

        except Exception as e:
            logger.warning("cache_read_error", node=node_name, error=str(e))
            return None

    # ---------------------------------------------------------
    # WRITE CACHE
    # ---------------------------------------------------------

    def write(self, input_data: str, result: Dict, node_name: str) -> None:

        if not self.settings.cache_enabled:
            return

        cache_key = self._hash_input(input_data, node_name)
        cache_path = self._get_cache_path(cache_key)

        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            logger.info(
                "cache_written",
                node=node_name,
                path=cache_path,
            )

        except Exception as e:
            logger.warning("cache_write_error", node=node_name, error=str(e))

    # ---------------------------------------------------------
    # CLEAR CACHE
    # ---------------------------------------------------------

    def clear(self, older_than_hours: float = 0) -> int:

        if not os.path.exists(self.cache_dir):
            return 0

        deleted = 0
        now = time.time()

        for filename in os.listdir(self.cache_dir):

            if not filename.endswith(".json"):
                continue

            filepath = os.path.join(self.cache_dir, filename)
            age = now - os.path.getmtime(filepath)

            if older_than_hours == 0 or age > older_than_hours * 3600:
                try:
                    os.remove(filepath)
                    deleted += 1
                except OSError:
                    pass

        logger.info("cache_cleared", deleted=deleted)
        return deleted

    # ---------------------------------------------------------
    # CACHE STATS
    # ---------------------------------------------------------

    def stats(self) -> Dict:

        if not os.path.exists(self.cache_dir):
            return {"enabled": self.settings.cache_enabled, "file_count": 0}

        files = [f for f in os.listdir(self.cache_dir) if f.endswith(".json")]

        if not files:
            return {"enabled": self.settings.cache_enabled, "file_count": 0}

        now = time.time()
        total_bytes = 0
        ages = []

        for filename in files:
            path = os.path.join(self.cache_dir, filename)

            try:
                total_bytes += os.path.getsize(path)
                ages.append((now - os.path.getmtime(path)) / 3600)
            except OSError:
                pass

        return {
            "enabled": self.settings.cache_enabled,
            "file_count": len(files),
            "total_size_kb": round(total_bytes / 1024, 1),
            "oldest_hours": round(max(ages), 1),
            "newest_hours": round(min(ages), 1),
            "ttl_hours": self.settings.cache_ttl_hours,
        }


# -------------------------------------------------------------
# SINGLETON ACCESS
# -------------------------------------------------------------

_cache_manager: Optional[CacheManager] = None


def get_cache() -> CacheManager:
    global _cache_manager

    if _cache_manager is None:
        _cache_manager = CacheManager()

    return _cache_manager