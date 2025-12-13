"""Module providing schema validation logic"""

from collections.abc import Callable
from typing import Any

from src.auto_structured_output.model import StringFormat, SupportedType


class SchemaValidator:
    """Validates JSON Schemas following OpenAI Structured Outputs specifications."""

    @classmethod
    def _validate_with_field_context(
        cls,
        field_name: str,
        error_prefix: str,
        validator: Callable[..., bool],
        *args: Any,
    ) -> None:
        try:
            validator(*args)
        except ValueError as e:
            raise ValueError(f"{error_prefix} for field '{field_name}': {e}") from e

    @classmethod
    def validate_type(cls, type_value: str | list[str]) -> bool:
        if isinstance(type_value, list):
            for t in type_value:
                if not SupportedType.is_supported_type(t):
                    raise ValueError(f"Type not supported: {t}")
            return True

        if not SupportedType.is_supported_type(type_value):
            raise ValueError(f"Type not supported: {type_value}")

        return True

    @classmethod
    def validate_string_format(cls, format_value: str) -> bool:
        if not StringFormat.is_supported_format(format_value):
            raise ValueError(f"String format not supported: {format_value}")

        return True

    @classmethod
    def validate_number_constraints(cls, constraints: dict[str, Any]) -> bool:
        valid_constraints = {
            "multipleOf",
            "maximum",
            "exclusiveMaximum",
            "minimum",
            "exclusiveMinimum",
        }
        metadata_fields = {"type", "description", "title", "default", "examples"}

        for key in constraints:
            if key not in valid_constraints and key not in metadata_fields:
                raise ValueError(f"Number constraint not supported: {key}")

        if "multipleOf" in constraints:
            if not isinstance(constraints["multipleOf"], (int, float)):
                raise ValueError("multipleOf must be a number")
            if constraints["multipleOf"] <= 0:
                raise ValueError("multipleOf must be a positive number")

        if "maximum" in constraints and "exclusiveMaximum" in constraints:
            raise ValueError("Cannot specify both maximum and exclusiveMaximum")

        if "minimum" in constraints and "exclusiveMinimum" in constraints:
            raise ValueError("Cannot specify both minimum and exclusiveMinimum")

        return True

    @classmethod
    def validate_array_constraints(cls, constraints: dict[str, Any]) -> bool:
        valid_constraints = {"minItems", "maxItems", "items"}
        metadata_fields = {"type", "description", "title", "default", "examples"}

        for key in constraints:
            if key not in valid_constraints and key not in metadata_fields:
                raise ValueError(f"Array constraint not supported: {key}")

        if "minItems" in constraints:
            if not isinstance(constraints["minItems"], int):
                raise ValueError("minItems must be an integer")
            if constraints["minItems"] < 0:
                raise ValueError("minItems must be 0 or greater")

        if "maxItems" in constraints:
            if not isinstance(constraints["maxItems"], int):
                raise ValueError("maxItems must be an integer")
            if constraints["maxItems"] < 0:
                raise ValueError("maxItems must be 0 or greater")

        if "minItems" in constraints and "maxItems" in constraints:
            if constraints["minItems"] > constraints["maxItems"]:
                raise ValueError("minItems must be less than or equal to maxItems")

        return True

    @classmethod
    def validate_required_fields(cls, required: list[str], properties: dict[str, Any]) -> bool:
        if not isinstance(required, list):
            raise ValueError("required must be a list")

        for field in required:
            if not isinstance(field, str):
                raise ValueError(f"Required field name must be a string: {field}")

            if field not in properties:
                raise ValueError(f"Required field '{field}' is not defined in properties")

        return True

    @classmethod
    def validate_enum(cls, enum_values: list[Any]) -> bool:
        if not isinstance(enum_values, list):
            raise ValueError("enum must be a list")

        if len(enum_values) == 0:
            raise ValueError("enum must have at least one value")

        if len(enum_values) != len(set(map(str, enum_values))):
            raise ValueError("enum values contain duplicates")

        return True

    @classmethod
    def validate_schema(cls, schema: dict[str, Any]) -> dict[str, Any]:
        if "type" not in schema:
            raise ValueError("Schema must have a 'type' field")

        if schema["type"] != "object":
            raise ValueError("Top-level schema must be of type 'object'")

        if "properties" not in schema:
            raise ValueError("Schema must have a 'properties' field")

        cls._validate_properties(schema["properties"])

        if "required" in schema:
            cls.validate_required_fields(schema["required"], schema["properties"])

        return schema

    @classmethod
    def _validate_properties(cls, properties: dict[str, Any]) -> None:
        if not isinstance(properties, dict):
            raise ValueError("properties must be a dictionary")

        for field_name, field_info in properties.items():
            if not isinstance(field_info, dict):
                raise ValueError(f"Field '{field_name}' definition is invalid")

            if "type" in field_info:
                field_type = field_info["type"]
                cls._validate_with_field_context(field_name, "Invalid type", cls.validate_type, field_type)

                if field_type == "string" and "format" in field_info:
                    cls._validate_with_field_context(
                        field_name, "Invalid format", cls.validate_string_format, field_info["format"]
                    )

                if field_type in ("number", "integer"):
                    cls._validate_with_field_context(
                        field_name, "Invalid constraints", cls.validate_number_constraints, field_info
                    )

                if field_type == "array":
                    cls._validate_with_field_context(
                        field_name, "Invalid array constraints", cls.validate_array_constraints, field_info
                    )

                    if "items" in field_info:
                        items = field_info["items"]
                        if isinstance(items, dict) and "type" in items:
                            if items["type"] == "object" and "properties" in items:
                                cls._validate_properties(items["properties"])

                if field_type == "object" and "properties" in field_info:
                    cls._validate_properties(field_info["properties"])

            if "enum" in field_info:
                cls._validate_with_field_context(field_name, "Invalid enum", cls.validate_enum, field_info["enum"])

            if "anyOf" in field_info:
                if not isinstance(field_info["anyOf"], list):
                    raise ValueError(f"'anyOf' for field '{field_name}' must be a list")
