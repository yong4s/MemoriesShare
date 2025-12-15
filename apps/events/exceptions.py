"""
Domain-specific business exceptions for Events app.

Following Clean Architecture principles:
- These are BUSINESS exceptions, not HTTP exceptions
- They represent domain logic failures
- HTTP mapping happens in the global exception handler
- Inherits from core business exception hierarchy
"""

from apps.shared.exceptions import AppError
from apps.shared.exceptions import BusinessRuleViolation
from apps.shared.exceptions import PermissionError
from apps.shared.exceptions import ResourceNotFoundError
from apps.shared.exceptions import ValidationError

# =============================================================================
# Event Domain Exceptions
# =============================================================================


class EventNotFoundError(ResourceNotFoundError):
    """Raised when requested event does not exist."""

    def __init__(self, event_identifier: str = None, **kwargs):
        message = "Event not found"
        if event_identifier:
            message = f"Event '{event_identifier}' not found"
        super().__init__(message, error_code="event_not_found", **kwargs)


class EventPermissionError(PermissionError):
    """Raised when user lacks permission to access/modify event."""

    def __init__(self, action: str = None, event_id: str = None, **kwargs):
        if action and event_id:
            message = f"Permission denied for '{action}' on event '{event_id}'"
        else:
            message = "Permission denied for this event operation"
        super().__init__(message, error_code="event_permission_denied", **kwargs)


class EventValidationError(ValidationError):
    """Raised when event data fails business validation."""

    def __init__(self, message: str = "Event validation failed", **kwargs):
        super().__init__(message, error_code="event_validation_error", **kwargs)


class EventBusinessRuleError(BusinessRuleViolation):
    """Raised when event operation violates business rules."""

    def __init__(self, rule_name: str, details: str = None, **kwargs):
        message = f"Event business rule violation: {rule_name}"
        if details:
            message = f"{message}. {details}"
        super().__init__(
            message, error_code=f"event_{rule_name.lower()}_violation", **kwargs
        )


# =============================================================================
# Participant Domain Exceptions
# =============================================================================


class ParticipantNotFoundError(ResourceNotFoundError):
    """Raised when requested participant does not exist."""

    def __init__(self, participant_identifier: str = None, **kwargs):
        message = "Participant not found"
        if participant_identifier:
            message = f"Participant '{participant_identifier}' not found"
        super().__init__(message, error_code="participant_not_found", **kwargs)


class ParticipantError(BusinessRuleViolation):
    """Raised when participant operation violates business rules."""

    def __init__(self, operation: str, reason: str, **kwargs):
        message = f"Participant {operation} failed: {reason}"
        super().__init__(
            message, error_code=f"participant_{operation}_failed", **kwargs
        )


# =============================================================================
# Specific Event Business Rules (convenience classes)
# =============================================================================


class EventCreationError(EventBusinessRuleError):
    """Raised when event creation fails due to business constraints."""

    def __init__(self, details: str, **kwargs):
        super().__init__("creation_failed", details, **kwargs)


class PastEventModificationError(EventBusinessRuleError):
    """Raised when trying to modify past events."""

    def __init__(self, action: str = "modification", **kwargs):
        details = f"Cannot perform {action} on past events"
        super().__init__("past_event_modification", details, **kwargs)


class EventCapacityExceededError(EventBusinessRuleError):
    """Raised when event capacity is exceeded."""

    def __init__(self, current: int, max_capacity: int, **kwargs):
        details = f"Event capacity exceeded ({current}/{max_capacity})"
        super().__init__("capacity_exceeded", details, **kwargs)


class OwnerRemovalError(ParticipantError):
    """Raised when trying to remove event owner."""

    def __init__(self, **kwargs):
        super().__init__("removal", "Cannot remove event owner", **kwargs)


class DuplicateParticipantError(ParticipantError):
    """Raised when trying to add existing participant."""

    def __init__(self, user_identifier: str = None, **kwargs):
        reason = (
            f"User '{user_identifier}' is already a participant"
            if user_identifier
            else "User is already a participant"
        )
        super().__init__("addition", reason, **kwargs)
