"""
Enterprise-grade DRF Exception Handler for Media Flow

This is the HEART of our exception architecture:
- Translates business exceptions → HTTP responses
- Provides consistent error format across all APIs
- Implements proper logging strategy
- Handles both our business exceptions and DRF exceptions

Architecture Flow:
DAL (Django exceptions) → Business exceptions → API Handler → HTTP responses

No more try/except in views!
"""

import logging
import traceback
from typing import Dict, Any, Optional

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import (
    ValidationError as DRFValidationError,
    AuthenticationFailed,
    PermissionDenied as DRFPermissionDenied,
    NotFound as DRFNotFound,
    APIException
)
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404

from apps.shared.exceptions import (
    AppError,
    ResourceNotFoundError,
    BusinessRuleViolation,
    ValidationError,
    PermissionError,
    ServiceUnavailableError,
    AuthenticationError,
    ConfigurationError,
)

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Enterprise exception handler with proper business → HTTP translation.
    
    This function is called for EVERY exception in DRF views.
    It translates business exceptions to HTTP responses with consistent format.
    
    Args:
        exc: The exception instance
        context: View context (request, view, args, kwargs)
        
    Returns:
        Response with error details and appropriate HTTP status
    """
    
    # Get request info for logging context
    request = context.get('request')
    view = context.get('view')
    
    request_info = _extract_request_info(request, view)
    
    # First, let DRF handle its standard exceptions (ValidationError, etc.)
    response = exception_handler(exc, context)
    if response is not None:
        # DRF handled it, but we still want to log and format it consistently
        _log_drf_exception(exc, request_info)
        return _format_drf_response(response, exc)

    # Now handle OUR business exceptions
    if isinstance(exc, ResourceNotFoundError):
        return _handle_resource_not_found(exc, request_info)
        
    elif isinstance(exc, BusinessRuleViolation):
        return _handle_business_rule_violation(exc, request_info)
        
    elif isinstance(exc, ValidationError):
        return _handle_validation_error(exc, request_info)
        
    elif isinstance(exc, PermissionError):
        return _handle_permission_error(exc, request_info)
        
    elif isinstance(exc, ServiceUnavailableError):
        return _handle_service_unavailable(exc, request_info)
        
    elif isinstance(exc, AuthenticationError):
        return _handle_authentication_error(exc, request_info)
        
    elif isinstance(exc, AppError):
        # Generic fallback for other business errors
        return _handle_generic_app_error(exc, request_info)
    
    # Handle legacy Django exceptions that might leak through
    elif isinstance(exc, (DjangoPermissionDenied, DRFPermissionDenied)):
        return _handle_django_permission_denied(exc, request_info)
        
    elif isinstance(exc, Http404):
        return _handle_django_404(exc, request_info)

    # Unhandled exception - this is a 500 error
    return _handle_unhandled_exception(exc, request_info)


# =============================================================================
# Business Exception Handlers
# =============================================================================

def _handle_resource_not_found(exc: ResourceNotFoundError, request_info: dict) -> Response:
    """Handle resource not found errors → 404"""
    _log_business_exception(exc, request_info, level='info')
    
    return Response({
        'error': 'Resource Not Found',
        'error_code': exc.error_code,
        'message': str(exc),
        'details': exc.get_context(),
        'timestamp': _get_timestamp(),
    }, status=status.HTTP_404_NOT_FOUND)


def _handle_business_rule_violation(exc: BusinessRuleViolation, request_info: dict) -> Response:
    """Handle business rule violations → 409 or 400"""
    _log_business_exception(exc, request_info, level='warning')
    
    # Some business rules are conflicts (409), others are bad requests (400)
    status_code = status.HTTP_409_CONFLICT
    if 'validation' in exc.error_code.lower() or 'invalid' in exc.error_code.lower():
        status_code = status.HTTP_400_BAD_REQUEST
    
    return Response({
        'error': 'Business Rule Violation',
        'error_code': exc.error_code,
        'message': str(exc),
        'details': exc.get_context(),
        'timestamp': _get_timestamp(),
    }, status=status_code)


def _handle_validation_error(exc: ValidationError, request_info: dict) -> Response:
    """Handle validation errors → 400"""
    _log_business_exception(exc, request_info, level='info')
    
    response_data = {
        'error': 'Validation Error',
        'error_code': exc.error_code,
        'message': str(exc),
        'timestamp': _get_timestamp(),
    }
    
    # Include field-specific errors if available
    if hasattr(exc, 'field_errors') and exc.field_errors:
        response_data['field_errors'] = exc.field_errors
        
    return Response(response_data, status=status.HTTP_400_BAD_REQUEST)


def _handle_permission_error(exc: PermissionError, request_info: dict) -> Response:
    """Handle permission errors → 403"""
    _log_business_exception(exc, request_info, level='warning')
    
    return Response({
        'error': 'Permission Denied',
        'error_code': exc.error_code,
        'message': str(exc),
        'details': exc.get_context(),
        'timestamp': _get_timestamp(),
    }, status=status.HTTP_403_FORBIDDEN)


def _handle_service_unavailable(exc: ServiceUnavailableError, request_info: dict) -> Response:
    """Handle service unavailable errors → 503"""
    _log_business_exception(exc, request_info, level='error')
    
    return Response({
        'error': 'Service Unavailable',
        'error_code': exc.error_code,
        'message': 'A required service is temporarily unavailable',
        'details': {'service_error': str(exc)},
        'timestamp': _get_timestamp(),
    }, status=status.HTTP_503_SERVICE_UNAVAILABLE)


def _handle_authentication_error(exc: AuthenticationError, request_info: dict) -> Response:
    """Handle authentication errors → 401"""
    _log_business_exception(exc, request_info, level='warning')
    
    return Response({
        'error': 'Authentication Failed',
        'error_code': exc.error_code,
        'message': str(exc),
        'timestamp': _get_timestamp(),
    }, status=status.HTTP_401_UNAUTHORIZED)


def _handle_generic_app_error(exc: AppError, request_info: dict) -> Response:
    """Handle generic app errors → 400"""
    _log_business_exception(exc, request_info, level='error')
    
    return Response({
        'error': 'Application Error',
        'error_code': exc.error_code,
        'message': str(exc),
        'details': exc.get_context(),
        'timestamp': _get_timestamp(),
    }, status=status.HTTP_400_BAD_REQUEST)


# =============================================================================
# Legacy Exception Handlers (Django exceptions that leak through)
# =============================================================================

def _handle_django_permission_denied(exc, request_info: dict) -> Response:
    """Handle legacy Django PermissionDenied"""
    logger.warning(f"Legacy Django PermissionDenied caught in API handler: {request_info}")
    
    return Response({
        'error': 'Permission Denied',
        'error_code': 'django_permission_denied',
        'message': 'Access denied',
        'timestamp': _get_timestamp(),
    }, status=status.HTTP_403_FORBIDDEN)


def _handle_django_404(exc, request_info: dict) -> Response:
    """Handle legacy Django Http404"""
    logger.info(f"Django Http404 caught in API handler: {request_info}")
    
    return Response({
        'error': 'Not Found',
        'error_code': 'resource_not_found',
        'message': 'The requested resource was not found',
        'timestamp': _get_timestamp(),
    }, status=status.HTTP_404_NOT_FOUND)


def _handle_unhandled_exception(exc, request_info: dict) -> Response:
    """Handle unexpected exceptions → 500"""
    # This is a critical error - log with full traceback
    logger.error(
        f"UNHANDLED EXCEPTION in API: {type(exc).__name__}: {str(exc)}\n"
        f"Request: {request_info}\n"
        f"Traceback: {traceback.format_exc()}"
    )
    
    # In production, don't expose internal error details
    return Response({
        'error': 'Internal Server Error',
        'error_code': 'internal_server_error',
        'message': 'An unexpected error occurred. Please try again later.',
        'timestamp': _get_timestamp(),
        # Include exception details only in DEBUG mode
        'details': _get_debug_details(exc) if _is_debug_mode() else {},
    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# =============================================================================
# Utility Functions
# =============================================================================

def _format_drf_response(response: Response, exc: Exception) -> Response:
    """Format DRF responses to match our consistent error format"""
    # DRF responses are already proper, but we can enhance them
    if hasattr(response, 'data') and isinstance(response.data, dict):
        response.data['timestamp'] = _get_timestamp()
        response.data['error_code'] = getattr(exc, 'default_code', type(exc).__name__)
    
    return response


def _extract_request_info(request, view) -> dict:
    """Extract useful request info for logging"""
    if not request:
        return {'method': 'unknown', 'path': 'unknown', 'user': 'unknown'}
        
    return {
        'method': getattr(request, 'method', 'unknown'),
        'path': getattr(request, 'path', 'unknown'),
        'user': getattr(request.user, 'id', 'anonymous') if hasattr(request, 'user') else 'unknown',
        'view': f"{view.__class__.__module__}.{view.__class__.__name__}" if view else 'unknown',
    }


def _log_business_exception(exc: AppError, request_info: dict, level: str = 'warning'):
    """Log business exceptions with appropriate level"""
    log_msg = f"Business exception in API: {type(exc).__name__}: {str(exc)} | Request: {request_info}"
    
    if level == 'info':
        logger.info(log_msg)
    elif level == 'warning':
        logger.warning(log_msg)
    elif level == 'error':
        logger.error(log_msg)
    else:
        logger.warning(log_msg)


def _log_drf_exception(exc: Exception, request_info: dict):
    """Log DRF exceptions"""
    logger.info(f"DRF exception in API: {type(exc).__name__}: {str(exc)} | Request: {request_info}")


def _get_timestamp() -> str:
    """Get ISO timestamp for error responses"""
    from datetime import datetime
    return datetime.utcnow().isoformat() + 'Z'


def _is_debug_mode() -> bool:
    """Check if we're in debug mode"""
    from django.conf import settings
    return getattr(settings, 'DEBUG', False)


def _get_debug_details(exc: Exception) -> dict:
    """Get debug details for development"""
    return {
        'exception_type': type(exc).__name__,
        'exception_message': str(exc),
        'traceback': traceback.format_exc().split('\n'),
    }