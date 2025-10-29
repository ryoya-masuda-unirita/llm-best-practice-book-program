"""Command side of CQRS - Handles knowledge base write operations asynchronously."""

import asyncio
import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

from src.client.chromadb_client import get_knowledge_collection
from src.logger import make_logger
from src.model.knowledge import KnowledgeRegisterCommand
from src.service.embedding_service import get_embedding

logger = make_logger(__name__)

# Thread pool for async operations
executor = ThreadPoolExecutor(max_workers=4)


def _generate_embedding_text(command: KnowledgeRegisterCommand) -> str:
    """
    Generate text for embedding from the command data.

    This creates a semantic representation combining request parameters
    and response data for effective similarity search.
    """
    # Combine request and response information into searchable text
    text_parts = [
        f"Gender: {command.character_request.gender.value}",
        f"Age: {command.character_request.age}",
        f"Name: {command.character_response.first_name} {command.character_response.last_name}",
    ]

    # Add personality information
    for i, personality in enumerate(command.character_response.personalities, 1):
        text_parts.append(f"Personality {i}: {personality.short_personality} - {personality.description}")

    # Add additional instructions if provided
    if command.character_request.additional_instructions:
        text_parts.append(f"Instructions: {command.character_request.additional_instructions}")

    return " | ".join(text_parts)


async def _store_in_chromadb_async(command: KnowledgeRegisterCommand, job_id: str) -> None:
    """
    Store knowledge in ChromaDB with custom embeddings.

    This is an async operation that generates embeddings using OpenAI/Gemini APIs.
    """
    try:
        collection = get_knowledge_collection()

        # Generate embedding text
        document_text = _generate_embedding_text(command)

        # Generate embedding using the same provider as the character generation
        logger.info(f"Generating embedding using {command.provider} API for job_id: {job_id}")
        embedding_vector = await get_embedding(document_text, command.provider)

        # Prepare metadata
        metadata = {
            "job_id": job_id,
            "provider": command.provider,
            "model": command.model,
            "processing_time_ms": command.processing_time_ms,
            "gender": command.character_request.gender.value,
            "age": command.character_request.age,
            "first_name": command.character_response.first_name,
            "last_name": command.character_response.last_name,
            "created_at": time.time(),
        }

        # Add custom metadata if provided
        if command.metadata:
            metadata.update(command.metadata)

        # Store full data as JSON in the document
        full_data = {
            "character_request": command.character_request.model_dump(),
            "character_response": command.character_response.model_dump(),
            "provider": command.provider,
            "model": command.model,
            "prompt": command.prompt,
            "processing_time_ms": command.processing_time_ms,
        }

        # Add full data to metadata
        metadata["full_data_json"] = json.dumps(full_data)

        # Store in ChromaDB with custom embedding
        # Need to run this in executor as ChromaDB operations are blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            executor,
            lambda: collection.add(
                ids=[job_id],
                documents=[document_text],
                metadatas=[metadata],
                embeddings=[embedding_vector],  # Use custom embedding from OpenAI/Gemini
            ),
        )

        logger.info(
            f"Successfully stored knowledge with job_id: {job_id} "
            f"using {command.provider} embedding (dim: {len(embedding_vector)})"
        )

    except Exception as e:
        logger.error(f"Error storing knowledge with job_id {job_id}: {e}")
        raise


async def register_knowledge_async(command: KnowledgeRegisterCommand) -> str:
    """
    Register knowledge asynchronously.

    This is the main command handler that accepts write operations
    and processes them in the background without blocking.

    Args:
        command: Knowledge registration command

    Returns:
        job_id: Unique identifier for tracking the background operation
    """
    job_id = str(uuid.uuid4())

    logger.info(f"Accepting knowledge registration command with job_id: {job_id}")

    # Create async task for background processing
    asyncio.create_task(_store_in_chromadb_async(command, job_id))

    return job_id


async def register_knowledge_sync(command: KnowledgeRegisterCommand) -> str:
    """
    Register knowledge synchronously (for testing or when immediate consistency is needed).

    Args:
        command: Knowledge registration command

    Returns:
        job_id: Unique identifier for the stored knowledge
    """
    job_id = str(uuid.uuid4())

    logger.info(f"Registering knowledge synchronously with job_id: {job_id}")

    # Execute and wait for completion
    await _store_in_chromadb_async(command, job_id)

    return job_id
