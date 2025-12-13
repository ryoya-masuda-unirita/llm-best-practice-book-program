"""Main module for extracting structure from natural language prompts"""

import json
from pathlib import Path
from typing import Any

from openai import OpenAI
from pydantic import BaseModel
from src.auto_structured_output.model_builder import ModelBuilder
from src.auto_structured_output.schema_generator import SchemaGenerator


class ExtractionError(Exception):
    """Error during structure extraction"""

    pass


class SchemaValidationError(ExtractionError):
    """Schema validation error"""

    pass


class ModelBuildError(ExtractionError):
    """Model building error"""

    pass


class StructureExtractor:
    def __init__(self, llm_client: OpenAI, model: str, max_retries: int = 3):
        self.client = llm_client
        self.model = model
        self.schema_generator = SchemaGenerator(max_retries=max_retries)
        self.model_builder = ModelBuilder()

    def extract_structure(
        self,
        prompts: list[str],
        use_high_reasoning: bool = False,
    ) -> type[BaseModel]:
        """Extract structure from prompt(s) and return Pydantic model.

        Multiple prompts generate a unified schema. Use high_reasoning for unclear prompts.
        """
        try:
            schema_json = self._extract_schema_from_prompt(prompts, use_high_reasoning)
            validated_schema = self._validate_schema(schema_json)
            model_class = self._build_model(validated_schema)
            return model_class

        except SchemaValidationError:
            raise
        except ModelBuildError:
            raise
        except Exception as e:
            raise ExtractionError(f"Error occurred during structure extraction: {e}") from e

    @staticmethod
    def save_extracted_json(model: type[BaseModel], file_path: str | Path) -> None:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        schema = model.model_json_schema()

        with path.open("w", encoding="utf-8") as f:
            json.dump(schema, f, indent=2, ensure_ascii=False)

    @staticmethod
    def load_from_json(file_path: str | Path) -> type[BaseModel]:
        """Load a schema from a JSON file and build a Pydantic model."""
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Schema file not found: {file_path}")

        with path.open("r", encoding="utf-8") as f:
            schema = json.load(f)

        schema_generator = SchemaGenerator()
        model_builder = ModelBuilder()

        try:
            validated_schema = schema_generator.validate_schema(schema)
        except ValueError as e:
            raise SchemaValidationError(f"Failed to validate schema: {e}") from e

        try:
            return model_builder.build_model(validated_schema)
        except Exception as e:
            raise ModelBuildError(f"Failed to build model: {e}") from e

    def _extract_schema_from_prompt(self, prompts: list[str], use_high_reasoning: bool = False) -> dict[str, Any]:
        try:
            return self.schema_generator.extract_from_prompt(prompts, self.client, self.model, use_high_reasoning)
        except ValueError as e:
            if "Failed to generate valid schema" in str(e):
                raise SchemaValidationError(f"Schema validation failed after retries: {e}") from e
            raise ExtractionError(f"Failed to extract schema: {e}") from e
        except Exception as e:
            raise ExtractionError(f"Failed to extract schema: {e}") from e

    def _validate_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        try:
            return self.schema_generator.validate_schema(schema)
        except ValueError as e:
            raise SchemaValidationError(f"Failed to validate schema: {e}") from e

    def _build_model(self, schema: dict[str, Any]) -> type[BaseModel]:
        try:
            return self.model_builder.build_model(schema)
        except Exception as e:
            raise ModelBuildError(f"Failed to build model: {e}") from e
