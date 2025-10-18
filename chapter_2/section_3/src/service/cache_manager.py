"""Cache manager for storing and retrieving LLM responses."""

import hashlib
import json
import time
from pathlib import Path
from typing import Callable, Optional

from src.config import config
from src.logger import make_logger
from src.model.model import CharacterResponse

logger = make_logger(__name__)


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """
    Calculate cosine similarity between two vectors.

    Args:
        vec1: First vector
        vec2: Second vector

    Returns:
        Cosine similarity score (0-1)
    """
    if len(vec1) != len(vec2):
        raise ValueError("Vectors must have the same length")

    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = sum(a * a for a in vec1) ** 0.5
    magnitude2 = sum(b * b for b in vec2) ** 0.5

    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0

    return dot_product / (magnitude1 * magnitude2)


class CacheManager:
    """Manages caching of LLM responses with TTL support."""

    def __init__(self, cache_dir: str = ".cache", ttl: Optional[int] = None):
        """
        Initialize the cache manager.

        Args:
            cache_dir: Directory to store cache files
            ttl: Time-to-live in seconds (defaults to config.cache_ttl)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = ttl if ttl is not None else config.cache_ttl

    def _generate_cache_key(self, prompt: list, model: str, temperature: float) -> str:
        """
        Generate a unique cache key based on prompt, model, and temperature.

        Args:
            prompt: The prompt used for LLM request
            model: The model name
            temperature: The temperature parameter

        Returns:
            A unique cache key (hash)
        """
        cache_data = {
            "prompt": prompt,
            "model": model,
            "temperature": temperature,
        }
        cache_str = json.dumps(cache_data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(cache_str.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get the file path for a cache key."""
        return self.cache_dir / f"{cache_key}.json"

    def get(self, prompt: list, model: str, temperature: float) -> Optional[CharacterResponse]:
        """
        Retrieve a cached response if available and not expired.

        Args:
            prompt: The prompt used for LLM request
            model: The model name
            temperature: The temperature parameter

        Returns:
            Cached CharacterResponse if available and valid, None otherwise
        """
        cache_key = self._generate_cache_key(prompt, model, temperature)
        cache_path = self._get_cache_path(cache_key)

        if not cache_path.exists():
            logger.debug(f"Cache miss: {cache_key}")
            return None

        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cache_data = json.load(f)

            # Check if cache has expired
            cached_time = cache_data.get("timestamp", 0)
            current_time = time.time()
            if current_time - cached_time > self.ttl:
                logger.info(f"Cache expired: {cache_key} (age: {current_time - cached_time:.1f}s, ttl: {self.ttl}s)")
                # Remove expired cache file
                cache_path.unlink(missing_ok=True)
                return None

            # Reconstruct CharacterResponse from cached data
            response_data = cache_data.get("response")
            if response_data:
                logger.info(f"Cache hit: {cache_key} (age: {current_time - cached_time:.1f}s)")
                return CharacterResponse(**response_data)

        except (json.JSONDecodeError, KeyError, Exception) as e:
            logger.warning(f"Failed to load cache {cache_key}: {e}")
            # Remove corrupted cache file
            cache_path.unlink(missing_ok=True)

        return None

    def set(
        self,
        prompt: list,
        model: str,
        temperature: float,
        response: CharacterResponse,
    ) -> None:
        """
        Store a response in the cache.

        Args:
            prompt: The prompt used for LLM request
            model: The model name
            temperature: The temperature parameter
            response: The CharacterResponse to cache
        """
        cache_key = self._generate_cache_key(prompt, model, temperature)
        cache_path = self._get_cache_path(cache_key)

        cache_data = {
            "timestamp": time.time(),
            "prompt": prompt,
            "model": model,
            "temperature": temperature,
            "response": response.model_dump(),
        }

        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            logger.debug(f"Cached response: {cache_key}")
        except Exception as e:
            logger.error(f"Failed to cache response {cache_key}: {e}")

    def clear_expired(self) -> int:
        """
        Clear all expired cache entries.

        Returns:
            Number of expired entries cleared
        """
        cleared = 0
        current_time = time.time()

        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)
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
        """
        Clear all cache entries.

        Returns:
            Number of entries cleared
        """
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


class SemanticCacheManager:
    """Manages semantic caching using embeddings and cosine similarity."""

    def __init__(
        self,
        cache_dir: str = ".semantic_cache",
        ttl: Optional[int] = None,
        similarity_threshold: float = 0.95,
        embedding_func: Optional[Callable] = None,
    ):
        """
        Initialize the semantic cache manager.

        Args:
            cache_dir: Directory to store cache files
            ttl: Time-to-live in seconds (defaults to config.cache_ttl)
            similarity_threshold: Minimum cosine similarity for cache hit (0-1)
            embedding_func: Async function to generate embeddings
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = ttl if ttl is not None else config.cache_ttl
        self.similarity_threshold = similarity_threshold
        self.embedding_func = embedding_func

        # Index file to store all embeddings for faster lookup
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

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get the file path for a cache key."""
        return self.cache_dir / f"{cache_key}.json"

    async def get(self, prompt: list, model: str, temperature: float) -> Optional[CharacterResponse]:
        """
        Retrieve a cached response using semantic similarity.

        Args:
            prompt: The prompt used for LLM request
            model: The model name
            temperature: The temperature parameter

        Returns:
            Cached CharacterResponse if similar prompt found, None otherwise
        """
        if not self.embedding_func:
            logger.warning("No embedding function provided to SemanticCacheManager")
            return None

        try:
            # Generate embedding for current prompt
            query_embedding = await self.embedding_func(prompt)

            # Load index and find most similar cached prompt
            index = self._load_index()
            current_time = time.time()

            best_similarity = 0.0
            best_cache_key = None

            for cache_key, cache_info in index.items():
                # Check if cache has expired
                cached_time = cache_info.get("timestamp", 0)
                if current_time - cached_time > self.ttl:
                    logger.debug(f"Skipping expired cache: {cache_key}")
                    continue

                # Check if model and temperature match
                if cache_info.get("model") != model or cache_info.get("temperature") != temperature:
                    continue

                # Calculate similarity
                cached_embedding = cache_info.get("embedding")
                if not cached_embedding:
                    continue

                similarity = cosine_similarity(query_embedding, cached_embedding)

                if similarity > best_similarity:
                    best_similarity = similarity
                    best_cache_key = cache_key

            # Check if best match meets threshold
            if best_similarity >= self.similarity_threshold and best_cache_key:
                cache_path = self._get_cache_path(best_cache_key)

                if cache_path.exists():
                    with open(cache_path, "r", encoding="utf-8") as f:
                        cache_data = json.load(f)

                    response_data = cache_data.get("response")
                    if response_data:
                        logger.info(
                            f"Semantic cache hit: {best_cache_key} "
                            f"(similarity: {best_similarity:.3f}, threshold: {self.similarity_threshold})"
                        )
                        return CharacterResponse(**response_data)

            logger.debug(
                f"Semantic cache miss: best similarity {best_similarity:.3f} < threshold {self.similarity_threshold}"
            )
            return None

        except Exception as e:
            logger.warning(f"Failed to perform semantic cache lookup: {e}")
            return None

    async def set(
        self,
        prompt: list,
        model: str,
        temperature: float,
        response: CharacterResponse,
    ) -> None:
        """
        Store a response in the semantic cache.

        Args:
            prompt: The prompt used for LLM request
            model: The model name
            temperature: The temperature parameter
            response: The CharacterResponse to cache
        """
        if not self.embedding_func:
            logger.warning("No embedding function provided to SemanticCacheManager")
            return

        try:
            # Generate embedding for prompt
            embedding = await self.embedding_func(prompt)

            # Generate unique cache key
            cache_key = hashlib.sha256(
                json.dumps(
                    {"prompt": prompt, "model": model, "temperature": temperature, "timestamp": time.time()},
                    sort_keys=True,
                    ensure_ascii=False,
                ).encode()
            ).hexdigest()

            cache_path = self._get_cache_path(cache_key)

            # Store cache data
            cache_data = {
                "timestamp": time.time(),
                "prompt": prompt,
                "model": model,
                "temperature": temperature,
                "response": response.model_dump(),
            }

            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)

            # Update index with embedding
            index = self._load_index()
            index[cache_key] = {
                "timestamp": cache_data["timestamp"],
                "model": model,
                "temperature": temperature,
                "embedding": embedding,
            }
            self._save_index(index)

            logger.debug(f"Semantic cache stored: {cache_key}")

        except Exception as e:
            logger.error(f"Failed to store semantic cache: {e}")

    def clear_expired(self) -> int:
        """
        Clear all expired cache entries.

        Returns:
            Number of expired entries cleared
        """
        cleared = 0
        current_time = time.time()

        index = self._load_index()
        updated_index = {}

        for cache_key, cache_info in index.items():
            cached_time = cache_info.get("timestamp", 0)
            if current_time - cached_time > self.ttl:
                # Remove cache file
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
        """
        Clear all cache entries.

        Returns:
            Number of entries cleared
        """
        cleared = 0
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
                cleared += 1
            except Exception as e:
                logger.warning(f"Failed to remove semantic cache file {cache_file}: {e}")

        if cleared > 0:
            logger.info(f"Cleared all {cleared} semantic cache entries")
        return cleared
