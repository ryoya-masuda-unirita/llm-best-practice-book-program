"""Chain of Responsibility Pattern: Builds data processing pipelines between nodes."""

from abc import ABC, abstractmethod
from typing import Any, Callable

from src.logger import make_logger
from src.workflow.base import ExecutionContext

logger = make_logger(__name__)


class DataProcessor(ABC):
    """
    Chain of Responsibility Pattern: Base class for data processors.
    Each processor in the chain can process data and pass it to the next processor.
    """

    def __init__(self):
        """Initialize the data processor."""
        self._next_processor: DataProcessor | None = None

    def set_next(self, processor: "DataProcessor") -> "DataProcessor":
        """
        Set the next processor in the chain.

        Args:
            processor: Next processor

        Returns:
            The next processor for chaining
        """
        self._next_processor = processor
        return processor

    @abstractmethod
    async def process(self, data: Any, context: ExecutionContext) -> Any:
        """
        Process the data.

        Args:
            data: Input data
            context: Execution context

        Returns:
            Processed data
        """
        pass

    async def _pass_to_next(self, data: Any, context: ExecutionContext) -> Any:
        """
        Pass data to the next processor in the chain.

        Args:
            data: Input data
            context: Execution context

        Returns:
            Processed data from the chain
        """
        if self._next_processor:
            return await self._next_processor.process(data, context)
        return data


class ValidationProcessor(DataProcessor):
    """Processor for validating data."""

    async def process(self, data: Any, context: ExecutionContext) -> Any:
        """
        Validate data before passing to next processor.

        Args:
            data: Input data
            context: Execution context

        Returns:
            Validated data
        """
        logger.info("Validating data in chain")

        # Simple validation - can be extended
        if data is None:
            logger.warning("Received None data in validation processor")

        return await self._pass_to_next(data, context)


class TransformationProcessor(DataProcessor):
    """Processor for transforming data."""

    def __init__(self, transform_func: Callable | None = None):
        """
        Initialize transformation processor.

        Args:
            transform_func: Function to transform data
        """
        super().__init__()
        self.transform_func = transform_func

    async def process(self, data: Any, context: ExecutionContext) -> Any:
        """
        Transform data before passing to next processor.

        Args:
            data: Input data
            context: Execution context

        Returns:
            Transformed data
        """
        logger.info("Transforming data in chain")

        if self.transform_func:
            data = self.transform_func(data, context)

        return await self._pass_to_next(data, context)


class LoggingProcessor(DataProcessor):
    """Processor for logging data."""

    async def process(self, data: Any, context: ExecutionContext) -> Any:
        """
        Log data before passing to next processor.

        Args:
            data: Input data
            context: Execution context

        Returns:
            Unchanged data
        """
        logger.info(f"Processing data in chain: {str(data)[:100]}")
        return await self._pass_to_next(data, context)


class FilterProcessor(DataProcessor):
    """Processor for filtering data."""

    def __init__(self, filter_func: Callable | None = None):
        """
        Initialize filter processor.

        Args:
            filter_func: Function to filter data (returns True to keep)
        """
        super().__init__()
        self.filter_func = filter_func

    async def process(self, data: Any, context: ExecutionContext) -> Any:
        """
        Filter data before passing to next processor.

        Args:
            data: Input data
            context: Execution context

        Returns:
            Filtered data or None if filtered out
        """
        logger.info("Filtering data in chain")

        if self.filter_func and not self.filter_func(data, context):
            logger.info("Data filtered out")
            return None

        return await self._pass_to_next(data, context)


class AggregationProcessor(DataProcessor):
    """Processor for aggregating multiple data items."""

    def __init__(self):
        """Initialize aggregation processor."""
        super().__init__()
        self.aggregated_data: list[Any] = []

    async def process(self, data: Any, context: ExecutionContext) -> Any:
        """
        Aggregate data before passing to next processor.

        Args:
            data: Input data
            context: Execution context

        Returns:
            Aggregated data
        """
        logger.info("Aggregating data in chain")

        if isinstance(data, list):
            self.aggregated_data.extend(data)
        else:
            self.aggregated_data.append(data)

        return await self._pass_to_next(self.aggregated_data, context)


class ProcessingPipeline:
    """
    Manages a chain of data processors.
    Provides a simple interface for building and executing processing pipelines.
    """

    def __init__(self):
        """Initialize the processing pipeline."""
        self._first_processor: DataProcessor | None = None
        self._last_processor: DataProcessor | None = None

    def add_processor(self, processor: DataProcessor) -> "ProcessingPipeline":
        """
        Add a processor to the pipeline.

        Args:
            processor: Processor to add

        Returns:
            Self for chaining
        """
        if self._first_processor is None:
            self._first_processor = processor
            self._last_processor = processor
        else:
            self._last_processor.set_next(processor)
            self._last_processor = processor

        return self

    async def execute(self, data: Any, context: ExecutionContext) -> Any:
        """
        Execute the pipeline on input data.

        Args:
            data: Input data
            context: Execution context

        Returns:
            Processed data
        """
        if self._first_processor is None:
            return data

        return await self._first_processor.process(data, context)
