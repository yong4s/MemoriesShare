"""
Permission Interface for Service Decoupling

Provides a minimal interface for permission checking to break circular dependencies.
Services that need permission validation can depend on this interface rather than 
concrete permission service implementations.
"""

from abc import ABC, abstractmethod
from typing import Any


class IPermissionValidator(ABC):
    """
    Minimal interface for permission validation operations.
    
    This interface provides only the essential permission validation methods
    needed by dependent services, allowing them to decouple from the full
    EventPermissionService implementation.
    """

    @abstractmethod
    def validate_owner_access(self, event: Any, user_id: int) -> bool:
        """
        Validate that user is event owner (raises PermissionDenied if not).
        
        Args:
            event: Event object to check ownership for
            user_id: ID of user to validate
            
        Returns:
            True if validation passes
            
        Raises:
            PermissionDenied: If user is not the owner
        """
        pass

    @abstractmethod
    def validate_guest_or_owner_access(self, event: Any, user_id: int) -> bool:
        """
        Validate that user is owner or guest (raises PermissionDenied if not).
        
        Args:
            event: Event object to check access for
            user_id: ID of user to validate
            
        Returns:
            True if validation passes
            
        Raises:
            PermissionDenied: If user has no access
        """
        pass

    @abstractmethod
    def is_event_owner(self, event: Any, user_id: int) -> bool:
        """
        Check if user is event owner (returns boolean, no exception).
        
        Args:
            event: Event object to check ownership for
            user_id: ID of user to check
            
        Returns:
            True if user is owner, False otherwise
        """
        pass

    @abstractmethod
    def has_event_access(self, event: Any, user_id: int) -> bool:
        """
        Check if user has any access to event (returns boolean, no exception).
        
        Args:
            event: Event object to check access for  
            user_id: ID of user to check
            
        Returns:
            True if user has access, False otherwise
        """
        pass


class SimplePermissionValidator(IPermissionValidator):
    """
    Simple implementation of permission validation using direct event owner checks.
    
    This provides a fallback implementation that doesn't require the full
    EventPermissionService, useful for breaking circular dependencies during
    refactoring or for simple use cases.
    """

    def validate_owner_access(self, event: Any, user_id: int) -> bool:
        """Validate owner access using direct ownership check."""
        from rest_framework.exceptions import PermissionDenied
        import logging
        
        logger = logging.getLogger(__name__)
        
        if not self.is_event_owner(event, user_id):
            logger.warning(f'User {user_id} attempted to access event {event.id} without ownership')
            raise PermissionDenied('You do not have permission to access this event')
        
        return True

    def validate_guest_or_owner_access(self, event: Any, user_id: int) -> bool:
        """Validate guest or owner access using basic checks."""
        from rest_framework.exceptions import PermissionDenied
        import logging
        
        logger = logging.getLogger(__name__)
        
        if not self.has_event_access(event, user_id):
            logger.warning(f'User {user_id} attempted to access event {event.id} without permission')
            raise PermissionDenied('You do not have permission to access this event')
        
        return True

    def is_event_owner(self, event: Any, user_id: int) -> bool:
        """Check event ownership directly."""
        if not event or not user_id:
            return False
        
        # Direct ownership check using legacy user field or participant relationship
        if hasattr(event, 'user_id') and event.user_id:
            return event.user_id == user_id
        elif hasattr(event, 'user') and event.user:
            return event.user.pk == user_id
        
        return False

    def has_event_access(self, event: Any, user_id: int) -> bool:
        """Check event access using basic rules."""
        if not event:
            return False
            
        # Public events are accessible to everyone
        if getattr(event, 'is_public', False):
            return True
            
        if not user_id:
            return False
            
        # Owner always has access
        if self.is_event_owner(event, user_id):
            return True
            
        # Check if user is a participant (simple implementation)
        try:
            # Try to use the EventParticipant relationship
            from apps.events.models.event_participant import EventParticipant
            return EventParticipant.objects.filter(event=event, user_id=user_id).exists()
        except Exception:
            # Fallback: if we can't check participants, deny access
            return False