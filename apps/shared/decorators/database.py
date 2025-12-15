import logging
from collections.abc import Callable
from functools import wraps
from typing import Any
from typing import Dict
from typing import Optional
from typing import Type

from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import DatabaseError
from django.db import IntegrityError

from apps.shared.exceptions import ResourceNotFoundError
from apps.shared.exceptions import ServiceUnavailableError
from apps.shared.exceptions import ValidationError

logger = logging.getLogger(__name__)


class DatabaseErrorHandler:
    """
    Centralized database error handling with configurable mappings.
    Preserves error context while providing consistent exception translation.
    """

    def __init__(self, operation_type: str = "database_operation"):
        self.operation_type = operation_type
        self.error_mappings = {
            IntegrityError: self._handle_integrity_error,
            DjangoValidationError: self._handle_validation_error,
            DatabaseError: self._handle_database_error,
            ObjectDoesNotExist: self._handle_not_found_error,
        }

    def _handle_integrity_error(
        self, error: IntegrityError, context: dict[str, Any]
    ) -> ValidationError:
        """Handle database integrity constraint violations"""
        logger.warning(
            f"Integrity constraint violation in {self.operation_type}: {error}",
            extra={"operation": self.operation_type, "context": context},
        )
        return ValidationError(
            message=f"Data integrity violation: {error!s}",
            error_code=f"{self.operation_type}_integrity_error",
            context={
                "original_error": str(error),
                "constraint_violation": True,
                **context,
            },
        )

    def _handle_validation_error(
        self, error: DjangoValidationError, context: dict[str, Any]
    ) -> ValidationError:
        """Handle Django validation errors while preserving field context"""
        logger.warning(
            f"Validation error in {self.operation_type}: {error}",
            extra={"operation": self.operation_type, "context": context},
        )

        # Preserve field-specific errors if available
        field_errors = {}
        if hasattr(error, "error_dict"):
            field_errors = error.error_dict
        elif hasattr(error, "error_list"):
            field_errors = {"non_field_errors": error.error_list}

        return ValidationError(
            message=f"Validation failed: {error!s}",
            field_errors=field_errors,
            error_code=f"{self.operation_type}_validation_error",
            context={
                "original_error": str(error),
                "django_validation": True,
                **context,
            },
        )

    def _handle_database_error(
        self, error: DatabaseError, context: dict[str, Any]
    ) -> ServiceUnavailableError:
        """Handle general database connectivity/infrastructure errors"""
        logger.critical(
            f"Database infrastructure error in {self.operation_type}: {error}",
            extra={"operation": self.operation_type, "context": context},
            exc_info=True,
        )
        return ServiceUnavailableError(
            message="Database service is temporarily unavailable",
            error_code=f"{self.operation_type}_database_error",
            context={
                "original_error": str(error),
                "infrastructure_failure": True,
                **context,
            },
        )

    def _handle_not_found_error(
        self, error: ObjectDoesNotExist, context: dict[str, Any]
    ) -> ResourceNotFoundError:
        """Handle object not found errors"""
        model_name = context.get("model_name", "Resource")
        identifier = context.get("identifier", "unknown")

        logger.debug(
            f"Resource not found in {self.operation_type}: {model_name} {identifier}",
            extra={"operation": self.operation_type, "context": context},
        )

        return ResourceNotFoundError(
            message=f"{model_name} not found",
            error_code=f"{model_name.lower()}_not_found",
            context={"identifier": identifier, "model": model_name, **context},
        )

    def handle_exception(self, error: Exception, context: dict[str, Any]) -> Exception:
        """
        Handle exception based on type mapping.
        Returns appropriate business exception or re-raises if unknown.
        """
        for error_type, handler in self.error_mappings.items():
            if isinstance(error, error_type):
                return handler(error, context)

        # For unexpected errors, log and re-raise
        logger.error(
            f"Unexpected error in {self.operation_type}: {error}",
            extra={"operation": self.operation_type, "context": context},
            exc_info=True,
        )

        return ServiceUnavailableError(
            message=f"Unexpected database error: {error!s}",
            error_code=f"{self.operation_type}_unexpected_error",
            context={"original_error": str(error), "unexpected": True, **context},
        )


def handle_db_errors(
    operation_type: str = None,
    model_name: str = None,
    preserve_context: bool = True,
    custom_mappings: dict[type[Exception], Callable] = None,
):
    """
    Decorator for centralized database error handling in DAL methods.

    Args:
        operation_type: Type of operation (create, read, update, delete)
        model_name: Model name for error context (auto-detected if not provided)
        preserve_context: Whether to preserve original error context
        custom_mappings: Additional error type mappings

    Usage:
        @handle_db_errors(operation_type='create', model_name='Event')
        def create_event(self, event_data: dict) -> Event:
            return Event.objects.create(**event_data)
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs) -> Any:
            # Auto-detect operation type from method name if not provided
            detected_operation = operation_type
            if not detected_operation:
                method_name = func.__name__.lower()
                if method_name.startswith("create"):
                    detected_operation = "create"
                elif method_name.startswith(("get", "find", "fetch")):
                    detected_operation = "read"
                elif method_name.startswith("update"):
                    detected_operation = "update"
                elif method_name.startswith("delete"):
                    detected_operation = "delete"
                else:
                    detected_operation = method_name

            # Create error handler
            error_handler = DatabaseErrorHandler(detected_operation)
            if custom_mappings:
                error_handler.error_mappings.update(custom_mappings)

            # Prepare context
            context = {
                "method": func.__name__,
                "class": self.__class__.__name__,
                "operation": detected_operation,
            }

            if model_name:
                context["model_name"] = model_name

            # Add method arguments to context if preserve_context is True
            if preserve_context:
                # Add non-sensitive argument info
                if args:
                    context["args_count"] = len(args)
                if kwargs:
                    # Filter out sensitive data like passwords
                    safe_kwargs = {
                        k: v
                        for k, v in kwargs.items()
                        if not any(
                            sensitive in k.lower()
                            for sensitive in ["password", "secret", "token", "key"]
                        )
                    }
                    context["kwargs"] = safe_kwargs

            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                business_exception = error_handler.handle_exception(e, context)
                raise business_exception from e

        return wrapper

    return decorator


# Convenience decorators for common operations
def handle_create_errors(model_name: str = None):
    """Decorator specifically for create operations"""
    return handle_db_errors(operation_type="create", model_name=model_name)


def handle_read_errors(model_name: str = None):
    """Decorator specifically for read operations"""
    return handle_db_errors(operation_type="read", model_name=model_name)


def handle_update_errors(model_name: str = None):
    """Decorator specifically for update operations"""
    return handle_db_errors(operation_type="update", model_name=model_name)


def handle_delete_errors(model_name: str = None):
    """Decorator specifically for delete operations"""
    return handle_db_errors(operation_type="delete", model_name=model_name)
