# -*- coding: utf-8 -*-
"""
auto-structured-output - Utilities for structured output extraction and validation.
"""

from src.auto_structured_output.extractor import (
    ExtractionError,
    ModelBuildError,
    SchemaValidationError,
    StructureExtractor,
)
from src.auto_structured_output.model import StringFormat, SupportedType
from src.auto_structured_output.model_builder import ModelBuilder
from src.auto_structured_output.schema_generator import SchemaGenerator
from src.auto_structured_output.validators import SchemaValidator

__version__ = "0.1.0"

__all__ = [
    "StructureExtractor",
    "SchemaGenerator",
    "ModelBuilder",
    "SchemaValidator",
    "SupportedType",
    "StringFormat",
    "ExtractionError",
    "SchemaValidationError",
    "ModelBuildError",
]
