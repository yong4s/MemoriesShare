"""
Domain-specific exceptions for Events app.

Following Clean Architecture principles, these exceptions are tightly coupled
to the events business domain and reside within the events app for high cohesion.
"""

from rest_framework.exceptions import APIException


class EventCreationError(APIException):
    """Exception raised when event creation fails due to business logic constraints."""

    status_code = 400
    default_detail = 'Error occurred while creating the event.'
    default_code = 'event_creation_error'


class EventNotFoundError(APIException):
    """Exception raised when requested event does not exist."""

    status_code = 404
    default_detail = 'Event not found.'
    default_code = 'event_not_found'


class EventPermissionError(APIException):
    """Exception raised when user lacks permission to access/modify event."""

    status_code = 403
    default_detail = 'Permission denied for this event.'
    default_code = 'event_permission_denied'


class InvalidEventDataError(APIException):
    """Exception raised when event data validation fails."""

    status_code = 400
    default_detail = 'Invalid event data provided.'
    default_code = 'invalid_event_data'


class EventDateValidationError(APIException):
    """Exception raised when event date validation fails."""

    status_code = 400
    default_detail = 'Invalid event date. Events cannot be created in the past.'
    default_code = 'invalid_event_date'


class EventCapacityExceededError(APIException):
    """Exception raised when event guest capacity is exceeded."""

    status_code = 400
    default_detail = 'Event guest capacity exceeded.'
    default_code = 'event_capacity_exceeded'


class EventModificationNotAllowedError(APIException):
    """Exception raised when event cannot be modified (e.g., past events)."""

    status_code = 403
    default_detail = 'Event modification not allowed at this time.'
    default_code = 'event_modification_not_allowed'


class EventDeletionNotAllowedError(APIException):
    """Exception raised when event cannot be deleted."""

    status_code = 403
    default_detail = 'Event deletion not allowed.'
    default_code = 'event_deletion_not_allowed'


class EventCategoryError(APIException):
    """Exception raised when event category operations fail."""

    status_code = 400
    default_detail = 'Invalid event category.'
    default_code = 'invalid_event_category'


class EventBaseException(APIException):
    """Base exception for all event-related errors"""
    status_code = 400
    default_detail = 'Event operation failed.'
    default_code = 'event_error'


class ParticipantError(EventBaseException):
    """Raised when participant operation fails"""
    status_code = 400
    default_detail = 'Participant operation failed.'
    default_code = 'participant_error'


class EventValidationError(EventBaseException):
    """Raised when event data validation fails"""
    status_code = 400
    default_detail = 'Event validation failed.'
    default_code = 'event_validation_error'


class EventBusinessRuleError(EventBaseException):
    """Raised when business rule validation fails"""
    status_code = 400
    default_detail = 'Business rule validation failed.'
    default_code = 'event_business_rule_error'
