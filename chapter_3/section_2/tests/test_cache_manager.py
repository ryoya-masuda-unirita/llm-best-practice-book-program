"""Tests for cache_manager module."""

import json
import time
from pathlib import Path

import pytest
from src.service.cache_manager import CacheManager


class TestCacheManager:
    """Test suite for CacheManager class."""

    def test_init_creates_cache_directory(self, temp_cache_dir):
        """Test that CacheManager creates cache directory on initialization."""
        cache_manager = CacheManager(cache_dir=temp_cache_dir)
        assert Path(temp_cache_dir).exists()
        assert cache_manager.cache_dir == Path(temp_cache_dir)

    @pytest.mark.parametrize("ttl", [100, 3600, 7200])
    def test_init_with_custom_ttl(self, temp_cache_dir, ttl):
        """Test CacheManager initialization with custom TTL values."""
        cache_manager = CacheManager(cache_dir=temp_cache_dir, ttl=ttl)
        assert cache_manager.ttl == ttl

    def test_generate_cache_key_consistent(self, temp_cache_dir, sample_prompt):
        """Test that cache key generation is consistent for same inputs."""
        cache_manager = CacheManager(cache_dir=temp_cache_dir)

        key1 = cache_manager._generate_cache_key(sample_prompt, "gpt-5.4")
        key2 = cache_manager._generate_cache_key(sample_prompt, "gpt-5.4")

        assert key1 == key2
        assert len(key1) == 64  # SHA256 hex digest length

    @pytest.mark.parametrize(
        "prompt,model,expected_different",
        [
            ([{"role": "system", "content": "test1"}], "gpt-5.4", True),
            ([{"role": "system", "content": "test"}], "gpt-5", True),
            ([{"role": "system", "content": "test"}], "gpt-5.4", True),
        ],
    )
    def test_generate_cache_key_unique_for_different_inputs(
        self, temp_cache_dir, sample_prompt, prompt, model, expected_different
    ):
        """Test that cache keys differ when inputs differ."""
        cache_manager = CacheManager(cache_dir=temp_cache_dir)

        key1 = cache_manager._generate_cache_key(sample_prompt, "gpt-5.4")
        key2 = cache_manager._generate_cache_key(prompt, model)

        if expected_different:
            assert key1 != key2

    def test_set_and_get_cache(self, temp_cache_dir, sample_prompt, sample_character_response):
        """Test setting and getting a cache entry."""
        cache_manager = CacheManager(cache_dir=temp_cache_dir, ttl=3600)

        # Set cache
        cache_manager.set(sample_prompt, "gpt-5.4", sample_character_response)

        # Get cache
        cached_response = cache_manager.get(sample_prompt, "gpt-5.4")

        assert cached_response is not None
        assert cached_response.first_name == sample_character_response.first_name
        assert cached_response.last_name == sample_character_response.last_name
        assert cached_response.age == sample_character_response.age
        assert cached_response.gender == sample_character_response.gender

    def test_get_cache_miss(self, temp_cache_dir, sample_prompt):
        """Test that get returns None for cache miss."""
        cache_manager = CacheManager(cache_dir=temp_cache_dir)

        cached_response = cache_manager.get(sample_prompt, "gpt-5.4")

        assert cached_response is None

    def test_cache_expiration(self, temp_cache_dir, sample_prompt, sample_character_response):
        """Test that expired cache entries are not returned."""
        cache_manager = CacheManager(cache_dir=temp_cache_dir, ttl=1)  # 1 second TTL

        # Set cache
        cache_manager.set(sample_prompt, "gpt-5.4", sample_character_response)

        # Wait for expiration
        time.sleep(1.1)

        # Try to get expired cache
        cached_response = cache_manager.get(sample_prompt, "gpt-5.4")

        assert cached_response is None

    def test_cache_file_structure(self, temp_cache_dir, sample_prompt, sample_character_response):
        """Test that cache file contains correct structure."""
        cache_manager = CacheManager(cache_dir=temp_cache_dir)

        cache_manager.set(sample_prompt, "gpt-5.4", sample_character_response)

        # Find the cache file
        cache_files = list(Path(temp_cache_dir).glob("*.json"))
        assert len(cache_files) == 1

        # Read and verify structure
        with open(cache_files[0], "r") as f:
            cache_data = json.load(f)

        assert "timestamp" in cache_data
        assert "prompt" in cache_data
        assert "model" in cache_data
        assert "response" in cache_data
        assert cache_data["model"] == "gpt-5.4"

    def test_corrupted_cache_file_handling(self, temp_cache_dir, sample_prompt, mocker):
        """Test that corrupted cache files are handled gracefully."""
        cache_manager = CacheManager(cache_dir=temp_cache_dir)

        # Create a corrupted cache file
        cache_key = cache_manager._generate_cache_key(sample_prompt, "gpt-5.4")
        cache_path = cache_manager._get_cache_path(cache_key)

        with open(cache_path, "w") as f:
            f.write("invalid json content")

        # Mock logger to verify warning is logged
        mock_logger = mocker.patch("src.service.cache_manager.logger")

        # Try to get corrupted cache
        cached_response = cache_manager.get(sample_prompt, "gpt-5.4")

        assert cached_response is None
        mock_logger.warning.assert_called_once()
        # Corrupted file should be removed
        assert not cache_path.exists()

    def test_clear_expired(self, temp_cache_dir, sample_prompt, sample_character_response):
        """Test clearing expired cache entries."""
        cache_manager = CacheManager(cache_dir=temp_cache_dir, ttl=1)

        # Set multiple cache entries
        cache_manager.set(sample_prompt, "gpt-5.4", sample_character_response)
        cache_manager.set(sample_prompt, "gpt-5", sample_character_response)

        # Wait for expiration
        time.sleep(1.1)

        # Add a fresh entry with a different model to avoid overwriting
        cache_manager_fresh = CacheManager(cache_dir=temp_cache_dir, ttl=3600)
        cache_manager_fresh.set(sample_prompt, "gpt-5.4-mini", sample_character_response)

        # Clear expired
        cleared = cache_manager.clear_expired()

        assert cleared == 2  # Two expired entries

        # Verify fresh entry still exists
        cache_files = list(Path(temp_cache_dir).glob("*.json"))
        assert len(cache_files) == 1

    def test_clear_all(self, temp_cache_dir, sample_prompt, sample_character_response):
        """Test clearing all cache entries."""
        cache_manager = CacheManager(cache_dir=temp_cache_dir)

        # Set multiple cache entries with different models
        cache_manager.set(sample_prompt, "gpt-5.4", sample_character_response)
        cache_manager.set(sample_prompt, "gpt-5", sample_character_response)
        cache_manager.set(sample_prompt, "gpt-5.4-mini", sample_character_response)

        # Clear all
        cleared = cache_manager.clear_all()

        assert cleared == 3

        # Verify all entries are removed
        cache_files = list(Path(temp_cache_dir).glob("*.json"))
        assert len(cache_files) == 0

    def test_set_cache_failure_handling(self, temp_cache_dir, sample_prompt, mocker):
        """Test that cache set failures are handled gracefully."""
        cache_manager = CacheManager(cache_dir=temp_cache_dir)

        # Mock the file write to raise an exception
        mock_logger = mocker.patch("src.service.cache_manager.logger")
        mocker.patch("builtins.open", side_effect=IOError("Disk full"))

        # Create a mock response
        mock_response = mocker.MagicMock()
        mock_response.model_dump.return_value = {"test": "data"}

        # Try to set cache (should not raise exception)
        cache_manager.set(sample_prompt, "gpt-5.4", mock_response)

        # Verify error was logged
        mock_logger.error.assert_called_once()

    @pytest.mark.parametrize(
        "ttl,wait_time,should_exist",
        [
            (5, 2, True),  # Cache still valid
            (1, 1.5, False),  # Cache expired
            (10, 0.5, True),  # Cache fresh
        ],
    )
    def test_cache_ttl_scenarios(
        self, temp_cache_dir, sample_prompt, sample_character_response, ttl, wait_time, should_exist
    ):
        """Test various cache TTL scenarios."""
        cache_manager = CacheManager(cache_dir=temp_cache_dir, ttl=ttl)

        # Set cache
        cache_manager.set(sample_prompt, "gpt-5.4", sample_character_response)

        # Wait
        time.sleep(wait_time)

        # Get cache
        cached_response = cache_manager.get(sample_prompt, "gpt-5.4")

        if should_exist:
            assert cached_response is not None
        else:
            assert cached_response is None
