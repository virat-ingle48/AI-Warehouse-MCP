from dataclasses import dataclass
from enum import Enum



class CommandType(str, Enum):
    ASSIGN_TASK = "ASSIGN_TASK"
    EMERGENCY_STOP = "EMERGENCY_STOP"


@dataclass
class ValidationResult:
    approved: bool
    reason: str=""

    @staticmethod
    def ok() -> "ValidationResult":
        return ValidationResult(approved=True)

    @staticmethod
    def reject(reason: str) -> "ValidationResult":
        return ValidationResult(approved=False, reason=reason)