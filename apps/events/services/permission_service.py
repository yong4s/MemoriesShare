import logging
from typing import Any

from apps.events.exceptions import EventPermissionError
from apps.events.models.event_participant import EventParticipant
from apps.shared.interfaces.permission_interface import IPermissionValidator

logger = logging.getLogger(__name__)


class EventPermissionService(IPermissionValidator):
    """Service for event permission checking and validation"""

    def __init__(self) -> None:
        pass

    def validate_event_access(self, event: Any, user_id: int, required_permission: str = 'access') -> bool:
        """Validate event access"""
        if not user_id:
            logger.warning('Access attempt without user ID')
            raise EventPermissionError(action=required_permission)

        if required_permission == 'owner':
            has_permission = self.is_event_owner(event, user_id)
        elif required_permission == 'access':
            has_permission = self.has_event_access(event, user_id)
        else:
            logger.error('Unknown permission type: %s', required_permission)
            has_permission = False

        if not has_permission:
            logger.warning(
                'Permission denied for user %s, event %s, permission %s',
                user_id,
                event.event_uuid,
                required_permission,
            )
            raise EventPermissionError(action=required_permission, event_id=str(event.event_uuid))

        return True

    def validate_owner_access(self, event: Any, user_id: int) -> bool:
        """Validate that user is event owner (raises PermissionDenied if not)"""
        return self.validate_event_access(event, user_id, 'owner')

    def validate_guest_or_owner_access(self, event: Any, user_id: int) -> bool:
        """Validate that user is owner or guest (raises PermissionDenied if not)"""
        return self.validate_event_access(event, user_id, 'access')

    def validate_participant_or_owner_access(self, event: Any, user_id: int) -> bool:
        """Validate that user is an actual participant (any role) of this event.

        Stricter than validate_guest_or_owner_access: ignores event.is_public so
        public-event readers cannot enumerate participant PII.
        """
        if not user_id:
            logger.warning('Participant access attempt without user ID')
            raise EventPermissionError(action='access')

        if not self.is_user_participant(event, user_id):
            logger.warning(
                'Participant access denied for user %s, event %s',
                user_id,
                event.event_uuid,
            )
            raise EventPermissionError(action='access', event_id=str(event.event_uuid))

        return True

    def validate_modify_access(self, event: Any, user_id: int) -> bool:
        """Validate that user can modify event (owner or moderator)"""
        if not user_id:
            logger.warning('Modify access attempt without user ID')
            raise EventPermissionError(action='modify')

        if not self.can_user_modify_event(event, user_id):
            logger.warning('Modify permission denied for user %s, event %s', user_id, event.event_uuid)
            raise EventPermissionError(action='modify', event_id=str(event.event_uuid))

        return True

    def is_event_owner(self, event: Any, user_id: int) -> bool:
        """Check if user is event owner via prefetched participants_through"""
        if not event or not user_id:
            return False

        for participation in event.participants_through.all():
            if participation.user_id == user_id and participation.role == EventParticipant.Role.OWNER:
                return True
        return False

    def has_event_access(self, event: Any, user_id: int) -> bool:
        """Check if user has access to event (public or participant)"""
        if not event:
            return False

        if event.is_public:
            return True

        if not user_id:
            return False

        return self.is_user_participant(event, user_id)

    def is_user_participant(self, event: Any, user_id: int) -> bool:
        """Check if user is an actual participant (any role) of the event."""
        if not event or not user_id:
            return False

        return any(p.user_id == user_id for p in event.participants_through.all())

    def can_user_access_event(self, event: Any, user_id: int) -> bool:
        """Check if user can access event"""
        return self.has_event_access(event, user_id)

    def can_user_modify_event(self, event: Any, user_id: int) -> bool:
        """Check if user can modify event (owner or moderator)"""
        if not event or not user_id:
            return False

        for participation in event.participants_through.all():
            if participation.user_id == user_id:
                return participation.role in [EventParticipant.Role.OWNER, EventParticipant.Role.MODERATOR]
        return False
