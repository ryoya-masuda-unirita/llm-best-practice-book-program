"""Cache manager for storing and retrieving LLM responses."""

import hashlib
import json
import time
from abc import ABC
from pathlib import Path
from typing import Callable, Optional

from src.config import config
from src.logger import make_logger
from src.model.model import CharacterResponse

logger = make_logger(__name__)


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    if len(vec1) != len(vec2):
        raise ValueError("Vectors must have the same length")

    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = sum(a * a for a in vec1) ** 0.5
    magnitude2 = sum(b * b for b in vec2) ** 0.5

    return 0.0 if (magnitude1 == 0 or magnitude2 == 0) else dot_product / (magnitude1 * magnitude2)


class BaseCacheManager(ABC):
    """Base class for cache managers with common TTL functionality."""

    def __init__(self, cache_dir: str, ttl: Optional[int] = None):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = ttl if ttl is not None else config.cache_ttl

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get the file path for a cache key."""
        return self.cache_dir / f"{cache_key}.json"

    def _is_expired(self, cached_time: float) -> bool:
        """Check if a cache entry has expired."""
        return time.time() - cached_time > self.ttl

    def _load_cache_file(self, cache_path: Path) -> Optional[dict]:
        """Load and parse a cache file."""
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Failed to load cache file {cache_path}: {e}")
            cache_path.unlink(missing_ok=True)
            return None

    def _save_cache_file(self, cache_path: Path, data: dict) -> None:
        """Save data to a cache file."""
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save cache file {cache_path}: {e}")

    def clear_expired(self) -> int:
        """Clear all expired cache entries."""
        cleared = 0
        current_time = time.time()

        for cache_file in self.cache_dir.glob("*.json"):
            try:
                cache_data = self._load_cache_file(cache_file)
                if cache_data:
                    cached_time = cache_data.get("timestamp", 0)
                    if current_time - cached_time > self.ttl:
                        cache_file.unlink()
                        cleared += 1
            except Exception as e:
                logger.warning(f"Failed to process cache file {cache_file}: {e}")
                cache_file.unlink(missing_ok=True)
                cleared += 1

        if cleared > 0:
            logger.info(f"Cleared {cleared} expired cache entries")
        return cleared

    def clear_all(self) -> int:
        """Clear all cache entries."""
        cleared = 0
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
                cleared += 1
            except Exception as e:
                logger.warning(f"Failed to remove cache file {cache_file}: {e}")

        if cleared > 0:
            logger.info(f"Cleared all {cleared} cache entries")
        return cleared


class CacheManager(BaseCacheManager):
    """Manages parameter-based caching of LLM responses with TTL support."""

    def __init__(self, cache_dir: str = ".cache", ttl: Optional[int] = None):
        """Initialize the cache manager."""
        super().__init__(cache_dir, ttl)

    def _generate_cache_key(self, prompt: list, model: str) -> str:
        """Generate a unique cache key based on prompt and model."""
        cache_data = {"prompt": prompt, "model": model}
        cache_str = json.dumps(cache_data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(cache_str.encode()).hexdigest()

    def get(self, prompt: list, model: str) -> Optional[CharacterResponse]:
        """Retrieve a cached response if available and not expired."""
        cache_key = self._generate_cache_key(prompt, model)
        cache_path = self._get_cache_path(cache_key)

        if not cache_path.exists():
            logger.debug(f"Cache miss: {cache_key}")
            return None

        cache_data = self._load_cache_file(cache_path)
        if not cache_data:
            return None

        cached_time = cache_data.get("timestamp", 0)
        if self._is_expired(cached_time):
            logger.info(f"Cache expired: {cache_key} (age: {time.time() - cached_time:.1f}s, ttl: {self.ttl}s)")
            cache_path.unlink(missing_ok=True)
            return None

        response_data = cache_data.get("response")
        if response_data:
            logger.info(f"Cache hit: {cache_key} (age: {time.time() - cached_time:.1f}s)")
            return CharacterResponse(**response_data)

        return None

    def set(self, prompt: list, model: str, response: CharacterResponse) -> None:
        """Store a response in the cache."""
        cache_key = self._generate_cache_key(prompt, model)
        cache_path = self._get_cache_path(cache_key)

        cache_data = {
            "timestamp": time.time(),
            "prompt": prompt,
            "model": model,
            "response": response.model_dump(),
        }

        self._save_cache_file(cache_path, cache_data)
        logger.debug(f"Cached response: {cache_key}")


class SemanticCacheManager(BaseCacheManager):
    """Manages semantic caching using embeddings and cosine similarity."""

    def __init__(
        self,
        cache_dir: str = ".semantic_cache",
        ttl: Optional[int] = None,
        similarity_threshold: float = 0.95,
        embedding_func: Optional[Callable] = None,
    ):
        super().__init__(cache_dir, ttl)
        self.similarity_threshold = similarity_threshold
        self.embedding_func = embedding_func
        self.index_file = self.cache_dir / "index.json"

    def _load_index(self) -> dict:
        """Load the embedding index from disk."""
        if not self.index_file.exists():
            return {}

        try:
            with open(self.index_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load semantic cache index: {e}")
            return {}

    def _save_index(self, index: dict) -> None:
        """Save the embedding index to disk."""
        try:
            with open(self.index_file, "w", encoding="utf-8") as f:
                json.dump(index, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save semantic cache index: {e}")

    def _find_similar_cache(self, query_embedding: list[float], model: str) -> tuple[Optional[str], float]:
        """Find the most similar cached prompt."""
        index = self._load_index()
        best_similarity = 0.0
        best_cache_key = None

        for cache_key, cache_info in index.items():
            if self._is_expired(cache_info.get("timestamp", 0)):
                continue
            if cache_info.get("model") != model:
                continue

            cached_embedding = cache_info.get("embedding")
            if not cached_embedding:
                continue

            similarity = cosine_similarity(query_embedding, cached_embedding)
            if similarity > best_similarity:
                best_similarity = similarity
                best_cache_key = cache_key

        return best_cache_key, best_similarity

    async def get(self, prompt: list, model: str) -> Optional[CharacterResponse]:
        """Retrieve a cached response using semantic similarity."""
        if not self.embedding_func:
            logger.warning("No embedding function provided to SemanticCacheManager")
            return None

        try:
            query_embedding = await self.embedding_func(prompt)
            cache_key, similarity = self._find_similar_cache(query_embedding, model)

            if similarity >= self.similarity_threshold and cache_key:
                cache_path = self._get_cache_path(cache_key)
                if cache_path.exists():
                    cache_data = self._load_cache_file(cache_path)
                    if cache_data:
                        response_data = cache_data.get("response")
                        if response_data:
                            logger.info(
                                f"Semantic cache hit: {cache_key} "
                                f"(similarity: {similarity:.3f}, threshold: {self.similarity_threshold})"
                            )
                            return CharacterResponse(**response_data)

            logger.debug(
                f"Semantic cache miss: best similarity {similarity:.3f} < threshold {self.similarity_threshold}"
            )

        except Exception as e:
            logger.warning(f"Failed to perform semantic cache lookup: {e}")

        return None

    async def set(self, prompt: list, model: str, response: CharacterResponse) -> None:
        """Store a response in the semantic cache."""
        if not self.embedding_func:
            logger.warning("No embedding function provided to SemanticCacheManager")
            return

        try:
            embedding = await self.embedding_func(prompt)

            timestamp = time.time()
            cache_key = hashlib.sha256(
                json.dumps(
                    {"prompt": prompt, "model": model, "timestamp": timestamp}, sort_keys=True, ensure_ascii=False
                ).encode()
            ).hexdigest()

            cache_path = self._get_cache_path(cache_key)
            cache_data = {
                "timestamp": timestamp,
                "prompt": prompt,
                "model": model,
                "response": response.model_dump(),
            }
            self._save_cache_file(cache_path, cache_data)

            index = self._load_index()
            index[cache_key] = {
                "timestamp": timestamp,
                "model": model,
                "embedding": embedding,
            }
            self._save_index(index)

            logger.debug(f"Semantic cache stored: {cache_key}")

        except Exception as e:
            logger.error(f"Failed to store semantic cache: {e}")

    def clear_expired(self) -> int:
        """Clear all expired cache entries and update index."""
        cleared = 0
        current_time = time.time()

        index = self._load_index()
        updated_index = {}

        for cache_key, cache_info in index.items():
            cached_time = cache_info.get("timestamp", 0)
            if current_time - cached_time > self.ttl:
                cache_path = self._get_cache_path(cache_key)
                cache_path.unlink(missing_ok=True)
                cleared += 1
            else:
                updated_index[cache_key] = cache_info

        self._save_index(updated_index)

        if cleared > 0:
            logger.info(f"Cleared {cleared} expired semantic cache entries")
        return cleared

    def clear_all(self) -> int:
        """Clear all cache entries and reset index."""
        cleared = super().clear_all()
        self._save_index({})
        return cleared
