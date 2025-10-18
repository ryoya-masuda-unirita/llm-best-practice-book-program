"""Tests for prompt storage functionality."""

import json
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import pytest
from src.model.prompt_data import PromptData
from src.service.prompt_storage import LocalFilePromptStorage, get_prompt_storage


class TestPromptData:
    """Tests for PromptData model."""

    @pytest.mark.parametrize(
        "prompt_id,prompt_content,response_content",
        [
            ("p001", "Simple prompt", "Simple response"),
            ("p002", ["msg1", "msg2"], {"key": "value"}),
            ("p003", {"role": "user", "content": "test"}, "test response"),
        ],
    )
    def test_create_prompt_data(self, prompt_id, prompt_content, response_content):
        """Test creating PromptData with various content types."""
        prompt_data = PromptData(
            prompt_id=prompt_id,
            prompt_content=prompt_content,
            response_content=response_content,
        )

        assert prompt_data.prompt_id == prompt_id
        assert prompt_data.prompt_content == prompt_content
        assert prompt_data.response_content == response_content
        assert prompt_data.created_at is not None
        assert prompt_data.metadata == {}

    def test_prompt_data_with_metadata(self):
        """Test PromptData with custom metadata."""
        metadata = {"request_id": "req-001", "user_id": "user-001"}
        prompt_data = PromptData(
            prompt_id="p001",
            prompt_content="test prompt",
            metadata=metadata,
        )

        assert prompt_data.metadata == metadata

    def test_created_at_auto_generation(self):
        """Test that created_at timestamp is automatically generated."""
        prompt_data = PromptData(
            prompt_id="p001",
            prompt_content="test prompt",
        )

        assert prompt_data.created_at is not None
        # Verify it's a valid ISO timestamp
        parsed_time = datetime.fromisoformat(prompt_data.created_at)
        assert isinstance(parsed_time, datetime)

    @pytest.mark.parametrize(
        "sensitive_text,pattern_name",
        [
            ("My SSN is 123-45-6789", "SSN"),
            ("Email me at test@example.com", "email"),
            ("Card: 1234-5678-9012-3456", "credit card"),
            ("Contact: user@domain.org for info", "email"),
            ("SSN: 987-65-4321 and email: admin@test.com", "multiple"),
        ],
    )
    def test_mask_sensitive_data_string(self, sensitive_text, pattern_name):
        """Test masking sensitive data in string content."""
        prompt_data = PromptData(
            prompt_id="p001",
            prompt_content=sensitive_text,
            response_content=sensitive_text,
        )

        prompt_data.mask_sensitive_data()

        # Verify SSN is masked
        if "SSN" in pattern_name or "multiple" in pattern_name:
            assert "***-**-****" in prompt_data.prompt_content
            assert "123-45-6789" not in prompt_data.prompt_content
            assert "987-65-4321" not in prompt_data.prompt_content

        # Verify email is masked
        if "email" in pattern_name or "multiple" in pattern_name:
            assert "***@***.***" in prompt_data.prompt_content
            assert "@example.com" not in prompt_data.prompt_content
            assert "@domain.org" not in prompt_data.prompt_content

        # Verify credit card is masked
        if "credit card" in pattern_name:
            assert "****-****-****-****" in prompt_data.prompt_content
            assert "1234-5678-9012-3456" not in prompt_data.prompt_content

    def test_mask_sensitive_data_in_list(self):
        """Test masking sensitive data in list structures."""
        prompt_data = PromptData(
            prompt_id="p001",
            prompt_content=[
                "My email is test@example.com",
                "SSN: 123-45-6789",
                "Regular text",
            ],
        )

        prompt_data.mask_sensitive_data()

        assert "***@***.***" in prompt_data.prompt_content[0]
        assert "test@example.com" not in prompt_data.prompt_content[0]
        assert "***-**-****" in prompt_data.prompt_content[1]
        assert "123-45-6789" not in prompt_data.prompt_content[1]
        assert prompt_data.prompt_content[2] == "Regular text"

    def test_mask_sensitive_data_in_dict(self):
        """Test masking sensitive data in dictionary structures."""
        prompt_data = PromptData(
            prompt_id="p001",
            prompt_content={
                "email": "user@example.com",
                "ssn": "123-45-6789",
                "message": "Contact admin@test.com",
            },
        )

        prompt_data.mask_sensitive_data()

        assert "***@***.***" in prompt_data.prompt_content["email"]
        assert "user@example.com" not in prompt_data.prompt_content["email"]
        assert "***-**-****" in prompt_data.prompt_content["ssn"]
        assert "123-45-6789" not in prompt_data.prompt_content["ssn"]

    def test_mask_sensitive_data_nested_structures(self):
        """Test masking in nested data structures."""
        prompt_data = PromptData(
            prompt_id="p001",
            prompt_content={
                "messages": [
                    {"role": "user", "content": "My email is test@example.com"},
                    {"role": "assistant", "content": "Card: 1234-5678-9012-3456"},
                ]
            },
        )

        prompt_data.mask_sensitive_data()

        content0 = prompt_data.prompt_content["messages"][0]["content"]
        content1 = prompt_data.prompt_content["messages"][1]["content"]

        assert "***@***.***" in content0
        assert "test@example.com" not in content0
        assert "****-****-****-****" in content1
        assert "1234-5678-9012-3456" not in content1

    def test_mask_sensitive_data_both_prompt_and_response(self):
        """Test masking sensitive data in both prompt and response content."""
        prompt_data = PromptData(
            prompt_id="p001",
            prompt_content="My email is prompt@example.com",
            response_content="Contact response@example.com",
        )

        prompt_data.mask_sensitive_data()

        assert "***@***.***" in prompt_data.prompt_content
        assert "prompt@example.com" not in prompt_data.prompt_content
        assert "***@***.***" in prompt_data.response_content
        assert "response@example.com" not in prompt_data.response_content

    def test_mask_sensitive_data_with_no_response(self):
        """Test masking when response_content is None."""
        prompt_data = PromptData(
            prompt_id="p001",
            prompt_content="Email: test@example.com",
            response_content=None,
        )

        # Should not raise error
        prompt_data.mask_sensitive_data()

        assert "***@***.***" in prompt_data.prompt_content
        assert prompt_data.response_content is None


@pytest.mark.asyncio
class TestLocalFilePromptStorage:
    """Tests for LocalFilePromptStorage."""

    @pytest.fixture
    def temp_storage_dir(self):
        """Create temporary storage directory for tests."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def storage(self, temp_storage_dir):
        """Create LocalFilePromptStorage instance with temp directory."""
        return LocalFilePromptStorage(base_dir=temp_storage_dir)

    async def test_save_prompt_basic(self, storage, temp_storage_dir):
        """Test basic prompt saving functionality."""
        prompt_data = PromptData(
            prompt_id="test-prompt-001",
            prompt_content="Test prompt content",
            response_content="Test response",
        )

        storage_path = await storage.save_prompt(prompt_data, mask_sensitive=False)

        assert storage_path is not None
        assert Path(storage_path).exists()
        assert temp_storage_dir in storage_path
        assert "test-prompt-001.json" in storage_path

    async def test_save_prompt_creates_date_partitions(self, storage, temp_storage_dir):
        """Test that save_prompt creates date-based directory structure."""
        prompt_data = PromptData(
            prompt_id="test-prompt-001",
            prompt_content="Test content",
        )

        storage_path = await storage.save_prompt(prompt_data, mask_sensitive=False)

        # Verify date-based directory structure exists
        # Structure is: base_dir/YYYY/MM/DD/file.json
        path = Path(storage_path)
        assert path.parent.parent.parent.parent == Path(temp_storage_dir)

        # Verify directories match current date
        now = datetime.utcnow()
        expected_structure = f"{now.year}/{now.month:02d}/{now.day:02d}"
        assert expected_structure in storage_path

    @pytest.mark.parametrize(
        "prompt_id",
        [
            "prompt-001",
            "prompt-with-dashes",
            "prompt_with_underscores",
            "prompt123",
        ],
    )
    async def test_save_prompt_with_different_ids(self, storage, prompt_id):
        """Test saving prompts with different ID formats."""
        prompt_data = PromptData(
            prompt_id=prompt_id,
            prompt_content="Test content",
        )

        storage_path = await storage.save_prompt(prompt_data, mask_sensitive=False)

        assert f"{prompt_id}.json" in storage_path
        assert Path(storage_path).exists()

    async def test_save_prompt_with_masking_enabled(self, storage):
        """Test saving prompt with sensitive data masking enabled."""
        prompt_data = PromptData(
            prompt_id="test-prompt-001",
            prompt_content="Email: sensitive@example.com",
            response_content="SSN: 123-45-6789",
        )

        storage_path = await storage.save_prompt(prompt_data, mask_sensitive=True)

        # Read back and verify masking was applied
        with open(storage_path, "r", encoding="utf-8") as f:
            saved_data = json.load(f)

        assert "sensitive@example.com" not in saved_data["prompt_content"]
        assert "***@***.***" in saved_data["prompt_content"]
        assert "123-45-6789" not in saved_data["response_content"]
        assert "***-**-****" in saved_data["response_content"]

    async def test_save_prompt_with_masking_disabled(self, storage):
        """Test saving prompt with masking disabled preserves original content."""
        prompt_data = PromptData(
            prompt_id="test-prompt-001",
            prompt_content="Email: sensitive@example.com",
        )

        storage_path = await storage.save_prompt(prompt_data, mask_sensitive=False)

        # Read back and verify no masking
        with open(storage_path, "r", encoding="utf-8") as f:
            saved_data = json.load(f)

        assert "sensitive@example.com" in saved_data["prompt_content"]

    async def test_save_prompt_with_complex_content(self, storage):
        """Test saving prompt with complex nested content."""
        prompt_data = PromptData(
            prompt_id="test-prompt-001",
            prompt_content={
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant"},
                    {"role": "user", "content": "Tell me a story"},
                ]
            },
            response_content={"text": "Once upon a time...", "metadata": {"tokens": 100}},
        )

        storage_path = await storage.save_prompt(prompt_data, mask_sensitive=False)

        # Verify content was saved correctly
        with open(storage_path, "r", encoding="utf-8") as f:
            saved_data = json.load(f)

        assert saved_data["prompt_content"]["messages"][0]["role"] == "system"
        assert saved_data["response_content"]["metadata"]["tokens"] == 100

    async def test_retrieve_prompt_basic(self, storage):
        """Test basic prompt retrieval."""
        # Save a prompt first
        original_data = PromptData(
            prompt_id="test-retrieve-001",
            prompt_content="Test content",
            response_content="Test response",
        )
        await storage.save_prompt(original_data, mask_sensitive=False)

        # Retrieve it
        retrieved_data = await storage.retrieve_prompt("test-retrieve-001")

        assert retrieved_data is not None
        assert retrieved_data.prompt_id == "test-retrieve-001"
        assert retrieved_data.prompt_content == "Test content"
        assert retrieved_data.response_content == "Test response"

    async def test_retrieve_nonexistent_prompt(self, storage):
        """Test retrieving a prompt that doesn't exist."""
        retrieved_data = await storage.retrieve_prompt("nonexistent-prompt-id")

        assert retrieved_data is None

    @pytest.mark.parametrize(
        "prompt_id,content",
        [
            ("p001", "Content 1"),
            ("p002", "Content 2"),
            ("p003", "Content 3"),
        ],
    )
    async def test_save_and_retrieve_multiple_prompts(self, storage, prompt_id, content):
        """Test saving and retrieving multiple prompts."""
        prompt_data = PromptData(
            prompt_id=prompt_id,
            prompt_content=content,
        )

        await storage.save_prompt(prompt_data, mask_sensitive=False)
        retrieved_data = await storage.retrieve_prompt(prompt_id)

        assert retrieved_data is not None
        assert retrieved_data.prompt_id == prompt_id
        assert retrieved_data.prompt_content == content

    async def test_retrieve_prompt_with_metadata(self, storage):
        """Test that metadata is preserved during save/retrieve."""
        metadata = {"request_id": "req-001", "user_id": "user-001"}
        prompt_data = PromptData(
            prompt_id="test-metadata-001",
            prompt_content="Test content",
            metadata=metadata,
        )

        await storage.save_prompt(prompt_data, mask_sensitive=False)
        retrieved_data = await storage.retrieve_prompt("test-metadata-001")

        assert retrieved_data is not None
        assert retrieved_data.metadata == metadata

    async def test_save_prompt_with_japanese_characters(self, storage):
        """Test saving and retrieving prompts with non-ASCII characters."""
        prompt_data = PromptData(
            prompt_id="test-japanese-001",
            prompt_content="これはテストです。日本語のプロンプトです。",
            response_content="こちらは応答です。",
        )

        await storage.save_prompt(prompt_data, mask_sensitive=False)
        retrieved_data = await storage.retrieve_prompt("test-japanese-001")

        assert retrieved_data is not None
        assert "これはテストです" in retrieved_data.prompt_content
        assert "こちらは応答です" in retrieved_data.response_content


class TestPromptStorageFactory:
    """Tests for prompt storage factory function."""

    def test_get_local_storage(self):
        """Test getting local file storage."""
        # Use tempfile to avoid creating directories in the working directory
        temp_dir = tempfile.mkdtemp(prefix="test_prompt_storage_")
        try:
            storage = get_prompt_storage("local", base_dir=temp_dir)

            assert isinstance(storage, LocalFilePromptStorage)
            assert storage.base_dir == Path(temp_dir)
        finally:
            # Cleanup
            if Path(temp_dir).exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

    def test_get_local_storage_with_custom_dir(self):
        """Test getting local storage with custom directory."""
        # Use tempfile to create a temporary directory
        custom_dir = tempfile.mkdtemp(prefix="custom_prompt_dir_")
        try:
            storage = get_prompt_storage("local", base_dir=custom_dir)

            assert isinstance(storage, LocalFilePromptStorage)
            assert storage.base_dir == Path(custom_dir)
        finally:
            # Cleanup
            if Path(custom_dir).exists():
                shutil.rmtree(custom_dir, ignore_errors=True)

    def test_get_unsupported_storage_type(self):
        """Test that unsupported storage type raises error."""
        with pytest.raises(ValueError, match="Unsupported storage type"):
            get_prompt_storage("unsupported_type")

    @pytest.mark.parametrize(
        "storage_type",
        [
            "s3",
            "gcs",
            "azure",
            "invalid",
        ],
    )
    def test_unsupported_storage_types(self, storage_type):
        """Test various unsupported storage types."""
        with pytest.raises(ValueError):
            get_prompt_storage(storage_type)
