"""
Common types and utilities for StageFlow.
"""

from dataclasses import dataclass
from enum import Enum
from typing import TypedDict

from rich.repr import auto


class ErrorType(Enum):
    PROCESS_VALIDATION = auto()

    def get_message(self) -> str:
        if self == self.PROCESS_VALIDATION:
            return "Invalid process definition"
        return ""


ErrorData = dict[str, str | list[str]]


class ErrorResultDict(TypedDict, total=False):
    type: str
    message: str  # Optional via total=False
    data: ErrorData


@dataclass
class ErrorResult:
    type: ErrorType
    data: ErrorData
    info: str | None

    def to_dict(self) -> ErrorResultDict:
        error_dict = ErrorResultDict(type=self.type.get_message(), data=self.data)
        if self.info:
            error_dict["message"] = self.info
        return error_dict
