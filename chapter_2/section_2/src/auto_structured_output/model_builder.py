"""Module for building Pydantic models from JSON schemas"""

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, create_model
from src.auto_structured_output.model import StringFormat, SupportedType


class ModelBuilder:
    def build_model(self, schema: dict[str, Any], model_name: str | None = None) -> type[BaseModel]:
        """Generate pydantic.BaseModel class from JSON schema."""
        if schema.get("type") != "object":
            raise ValueError("Top-level schema must be of type 'object'")

        name = model_name or schema.get("title", "DynamicModel")
        properties = schema.get("properties", {})
        required_fields = set(schema.get("required", []))

        fields = {}

        for field_name, field_info in properties.items():
            field_type = self._get_field_type(field_info)
            description = field_info.get("description")
            default_value = field_info.get("default", ...)

            if field_name in required_fields:
                if description:
                    fields[field_name] = (field_type, Field(..., description=description))
                else:
                    fields[field_name] = (field_type, ...)
            else:
                if default_value is ...:
                    default_value = None
                    field_type = Optional[field_type]  # type: ignore[valid-type, assignment]

                if description:
                    fields[field_name] = (
                        field_type,
                        Field(default_value, description=description),
                    )
                else:
                    fields[field_name] = (field_type, default_value)

        model_class: type[BaseModel] = create_model(name, **fields)  # type: ignore[call-overload]
        return model_class

    def _get_field_type(self, field_info: dict[str, Any]) -> type:
        if "anyOf" in field_info:
            return self._handle_any_of(field_info["anyOf"])

        if "enum" in field_info:
            return self._handle_enum(field_info)

        type_str = field_info.get("type", "string")

        # Multiple types (e.g., ["string", "null"])
        if isinstance(type_str, list):
            types = []
            for t in type_str:
                if SupportedType.is_supported_type(t):
                    types.append(SupportedType(t).to_type_mapping())
                else:
                    types.append(str)
            if len(types) == 1:
                return types[0]
            result_type: type = types[0]
            for t in types[1:]:
                result_type = result_type | t  # type: ignore[assignment]
            return result_type

        if "format" in field_info:
            if StringFormat.is_supported_format(field_info["format"]):
                return StringFormat(field_info["format"]).to_format_mapping()

        if type_str == "array":
            return self._handle_array(field_info)

        if type_str == "object":
            return self._handle_object(field_info)

        if SupportedType.is_supported_type(type_str):
            return SupportedType(type_str).to_type_mapping()
        return str

    def _handle_array(self, field_info: dict[str, Any]) -> type:
        if "items" not in field_info:
            return list

        items_info = field_info["items"]
        item_type = self._get_field_type(items_info)

        return list[item_type]  # type: ignore[valid-type]

    def _handle_object(self, field_info: dict[str, Any]) -> type:
        if "properties" not in field_info:
            return dict

        nested_model_name = field_info.get("title", "NestedModel")
        return self.build_model(field_info, nested_model_name)

    def _handle_enum(self, field_info: dict[str, Any]) -> type:
        enum_values = field_info["enum"]
        if not enum_values:
            return str
        return Literal[tuple(enum_values)]  # type: ignore[return-value]

    def _handle_any_of(self, any_of_list: list[dict[str, Any]]) -> type:
        if not any_of_list:
            return str

        types = [self._get_field_type(schema) for schema in any_of_list]

        if len(types) == 1:
            return types[0]

        result_type: type = types[0]
        for t in types[1:]:
            result_type = result_type | t  # type: ignore[assignment]
        return result_type
