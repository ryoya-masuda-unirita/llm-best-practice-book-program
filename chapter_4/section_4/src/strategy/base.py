"""Base strategy interface for RAG pipeline components."""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

InputType = TypeVar("InputType")
OutputType = TypeVar("OutputType")


class Component(ABC, Generic[InputType, OutputType]):
    """Base class for all pipeline components following the strategy pattern."""

    @abstractmethod
    async def process(self, input_data: InputType) -> OutputType:
        pass
