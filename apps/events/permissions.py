"""
Custom permissions for event operations using EventPermissionService
"""

from rest_framework.permissions import BasePermission

from apps.events.models.event import Event
from apps.shared.container import get_container


class IsEventOwnerOrModerator(BasePermission):
    """
    Permission to check if user can modify event (owner or moderator)
    """
    
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
        
        permission_service = get_container().permission_service()
        return permission_service.can_user_modify_event(event, request.user.id)


class CanAccessEvent(BasePermission):
    """
    Permission to check if user can access event (owner, moderator, or participant)
    """
    
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
        
        permission_service = get_container().permission_service()
        return permission_service.can_user_access_event(event, request.user.id)


class IsEventOwner(BasePermission):
    """
    Permission to check if user is event owner
    """
    
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
        
        permission_service = get_container().permission_service()
        return permission_service.is_event_owner(event, request.user.id)


class IsEventParticipant(BasePermission):
    """
    Permission to check if user is event participant
    """
    
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
        
        permission_service = get_container().permission_service()
        participation = permission_service.get_user_participation_in_event(event, request.user)
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