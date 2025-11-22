"""
Custom permissions for event operations using EventPermissionService
"""

from rest_framework.permissions import BasePermission

from apps.events.models.event import Event
from apps.events.services.permission_service import EventPermissionService


class IsEventOwnerOrModerator(BasePermission):
    """
    Permission to check if user can modify event (owner or moderator)
    """
    
    def __init__(self):
        self.permission_service = None
    
    def _get_permission_service(self):
        """Lazy initialization to avoid circular imports"""
        if self.permission_service is None:
            self.permission_service = EventPermissionService()
        return self.permission_service
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
            
        if isinstance(obj, Event):
            event = obj
        else:
            # If obj is not Event, try to get event from obj
            event = getattr(obj, 'event', None)
            if not event:
                return False
        
        return self._get_permission_service().can_user_modify_event(event, request.user.id)


class CanAccessEvent(BasePermission):
    """
    Permission to check if user can access event (owner, moderator, or participant)
    """
    
    def __init__(self):
        self.permission_service = None
    
    def _get_permission_service(self):
        """Lazy initialization to avoid circular imports"""
        if self.permission_service is None:
            self.permission_service = EventPermissionService()
        return self.permission_service
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
            
        if isinstance(obj, Event):
            event = obj
        else:
            # If obj is not Event, try to get event from obj
            event = getattr(obj, 'event', None)
            if not event:
                return False
        
        return self._get_permission_service().can_user_access_event(event, request.user.id)


class IsEventOwner(BasePermission):
    """
    Permission to check if user is event owner
    """
    
    def __init__(self):
        self.permission_service = None
    
    def _get_permission_service(self):
        """Lazy initialization to avoid circular imports"""
        if self.permission_service is None:
            self.permission_service = EventPermissionService()
        return self.permission_service
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
            
        if isinstance(obj, Event):
            event = obj
        else:
            # If obj is not Event, try to get event from obj
            event = getattr(obj, 'event', None)
            if not event:
                return False
        
        return self._get_permission_service().is_event_owner(event, request.user.id)


class IsEventParticipant(BasePermission):
    """
    Permission to check if user is event participant
    """
    
    def __init__(self):
        self.permission_service = None
    
    def _get_permission_service(self):
        """Lazy initialization to avoid circular imports"""
        if self.permission_service is None:
            self.permission_service = EventPermissionService()
        return self.permission_service
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
            
        if isinstance(obj, Event):
            event = obj
        else:
            # If obj is not Event, try to get event from obj
            event = getattr(obj, 'event', None)
            if not event:
                return False
        
        participation = self._get_permission_service().get_user_participation_in_event(event, request.user)
        return participation is not None


class EventPermissionMixin:
    """
    Mixin to provide event object for permission checks
    """
    
    def get_object(self):
        """Get event object based on URL parameter"""
        event_uuid = self.kwargs.get('event_uuid')
        if not event_uuid:
            return None
            
        from apps.events.dal.event_dal import EventDAL
        event_dal = EventDAL()
        
        try:
            return event_dal.get_event_by_uuid(event_uuid)
        except Exception:
            return None