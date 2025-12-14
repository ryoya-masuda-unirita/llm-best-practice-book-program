from datetime import date, datetime, time
from enum import StrEnum


class SupportedType(StrEnum):
    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"
    NULL = "null"
    ENUM = "enum"
    ANY_OF = "anyOf"

    @staticmethod
    def is_supported_type(_type: str) -> bool:
        return _type in SupportedType._value2member_map_

    def to_type_mapping(self) -> type:
        type_mapping: dict[str, type] = {
            SupportedType.STRING: str,
            SupportedType.INTEGER: int,
            SupportedType.NUMBER: float,
            SupportedType.BOOLEAN: bool,
            SupportedType.ARRAY: list,
            SupportedType.OBJECT: dict,
            SupportedType.NULL: type(None),
        }
        return type_mapping[self]


class StringFormat(StrEnum):
    DATE_TIME = "date-time"
    DATE = "date"
    TIME = "time"
    DURATION = "duration"
    EMAIL = "email"
    HOSTNAME = "hostname"
    IPV4 = "ipv4"
    IPV6 = "ipv6"
    UUID = "uuid"

    @staticmethod
    def is_supported_format(_format: str) -> bool:
        return _format in StringFormat._value2member_map_

    def to_format_mapping(self) -> type:
        format_mapping: dict[str, type] = {
            StringFormat.DATE_TIME: datetime,
            StringFormat.DATE: date,
            StringFormat.TIME: time,
            StringFormat.DURATION: str,
            StringFormat.EMAIL: str,
            StringFormat.HOSTNAME: str,
            StringFormat.IPV4: str,
            StringFormat.IPV6: str,
            StringFormat.UUID: str,
        }
        return format_mapping[self]
