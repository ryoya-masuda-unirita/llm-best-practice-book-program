"""Command side of CQRS - Handles knowledge base write operations asynchronously."""

import asyncio
import json
import time
import uuid

from src import executor
from src.client.chromadb_client import get_knowledge_collection
from src.logger import make_logger
from src.model.knowledge import KnowledgeRegisterCommand
from src.service.embedding_service import get_embedding

logger = make_logger(__name__)


def _generate_embedding_text(command: KnowledgeRegisterCommand) -> str:
    """Generate text for embedding from the command data."""
    text_parts = [
        f"Gender: {command.character_request.gender.value}",
        f"Age: {command.character_request.age}",
        f"Name: {command.character_response.first_name} {command.character_response.last_name}",
    ]

    for i, personality in enumerate(command.character_response.personalities, 1):
        text_parts.append(f"Personality {i}: {personality.short_personality} - {personality.description}")

    if command.character_request.additional_instructions:
        text_parts.append(f"Instructions: {command.character_request.additional_instructions}")

    return " | ".join(text_parts)


async def _store_in_chromadb_async(command: KnowledgeRegisterCommand, job_id: str) -> None:
    """Store knowledge in ChromaDB with Anthropic embeddings."""
    try:
        collection = get_knowledge_collection()
        document_text = _generate_embedding_text(command)

        logger.info(f"Generating Anthropic embedding for job_id: {job_id}")
        embedding_vector = await get_embedding(document_text)

        metadata = {
            "job_id": job_id,
            "model": command.model,
            "processing_time_ms": command.processing_time_ms,
            "gender": command.character_request.gender.value,
            "age": command.character_request.age,
            "first_name": command.character_response.first_name,
            "last_name": command.character_response.last_name,
            "created_at": time.time(),
        }

        if command.metadata:
            metadata.update(command.metadata)

        full_data = {
            "character_request": command.character_request.model_dump(),
            "character_response": command.character_response.model_dump(),
            "model": command.model,
            "prompt": command.prompt,
            "processing_time_ms": command.processing_time_ms,
        }

        metadata["full_data_json"] = json.dumps(full_data)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            executor,
            lambda: collection.add(
                ids=[job_id],
                documents=[document_text],
                metadatas=[metadata],
                embeddings=[embedding_vector],
            ),
        )

        logger.info(f"Successfully stored knowledge with job_id: {job_id} (embedding dim: {len(embedding_vector)})")

    except Exception as e:
        logger.error(f"Error storing knowledge with job_id {job_id}: {e}")
        raise


async def register_knowledge_async(command: KnowledgeRegisterCommand) -> str:
    """Register knowledge asynchronously."""
    job_id = str(uuid.uuid4())

    logger.info(f"Accepting knowledge registration command with job_id: {job_id}")

    asyncio.create_task(_store_in_chromadb_async(command, job_id))

    return job_id


async def register_knowledge_sync(command: KnowledgeRegisterCommand) -> str:
    """Register knowledge synchronously (for testing or when immediate consistency is needed)."""
    job_id = str(uuid.uuid4())

    logger.info(f"Registering knowledge synchronously with job_id: {job_id}")

    await _store_in_chromadb_async(command, job_id)

    return job_id
