"""Arogya AI — Domain Service Exceptions.

Module 3, Phase 3.6: Data Access Repositories & Clinical Domain Service Layer.
Defines typed domain exceptions for entity not found, cross-entity consistency
violations, duplicate records, and business validation errors.
"""


class DomainError(Exception):
    """Base exception for all Arogya AI domain service errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class EntityNotFoundError(DomainError):
    """Raised when an expected domain entity does not exist in persistence."""

    def __init__(self, entity_type: str, identifier: object) -> None:
        message = f"{entity_type} with identifier '{identifier}' was not found."
        super().__init__(message)
        self.entity_type = entity_type
        self.identifier = identifier


class ConsistencyError(DomainError):
    """Raised when cross-entity referential integrity or ownership invariants are violated."""

    pass


class DuplicateEntityError(DomainError):
    """Raised when an operation would violate unique natural key constraints (username, email, MRN)."""

    def __init__(self, entity_type: str, field_name: str, value: str) -> None:
        message = f"{entity_type} with {field_name} '{value}' already exists."
        super().__init__(message)
        self.entity_type = entity_type
        self.field_name = field_name
        self.value = value


class DomainValidationError(DomainError):
    """Raised when domain business validation rules fail."""

    pass
