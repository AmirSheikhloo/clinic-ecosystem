"""Patient application errors."""

from __future__ import annotations


class PatientApplicationError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class PatientValidationError(PatientApplicationError):
    def __init__(self, message: str) -> None:
        super().__init__("patient_validation_error", message)


class PatientNotFound(PatientApplicationError):
    def __init__(self) -> None:
        super().__init__("patient_not_found", "Patient not found")
