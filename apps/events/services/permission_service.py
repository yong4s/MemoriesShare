import logging
from typing import Any
from typing import Dict

from apps.accounts.services import UserService
from apps.events.dal.event_dal import EventDAL
from apps.events.dal.event_participant_dal import EventParticipantDAL
from apps.events.exceptions import EventPermissionError
from apps.events.models.event_participant import EventParticipant
from apps.shared.exceptions import PermissionError
from apps.shared.interfaces.permission_interface import IPermissionValidator

logger = logging.getLogger(__name__)


class EventPermissionService(IPermissionValidator):
    """Service for event permission checking and validation"""

    def __init__(
        self,
        dal: EventDAL | None = None,
        participant_dal: EventParticipantDAL | None = None,
        user_service: UserService | None = None,
    ) -> None:
        self.dal = dal or EventDAL()
        self.participant_dal = participant_dal or EventParticipantDAL()
        self.user_service = user_service or UserService()

    # =============================================================================
    # PERMISSION VALIDATION (main methods)
    # =============================================================================

    def validate_event_access(self, event: Any, user_id: int, required_permission: str = 'access') -> bool:
        """Validate event access"""
        if not user_id:
            logger.warning('Access attempt without user ID')
            raise EventPermissionError(action=required_permission)

        has_permission = self._check_permission(event, user_id, required_permission)

        if not has_permission:
            logger.warning(
                f'Permission denied for user {user_id}, event {event.event_uuid}, permission {required_permission}'
            )
            raise EventPermissionError(action=required_permission, event_id=str(event.event_uuid))

        return True

    def _check_permission(self, event, user_id, required_permission):
        """Internal permission checking logic"""
        if required_permission == 'owner':
            return self.is_event_owner(event, user_id)
        if required_permission == 'guest':
            return self.is_event_guest(event, user_id)
        if required_permission == 'access':
            return self.has_event_access(event, user_id)
        logger.error(f'Unknown permission type: {required_permission}')
        return False

    def validate_owner_access(self, event, user_id):
        """Validate that user is event owner (raises PermissionDenied if not)"""
        return self.validate_event_access(event, user_id, 'owner')

    def validate_guest_or_owner_access(self, event, user_id):
        """Validate that user is owner or guest (raises PermissionDenied if not)"""
        return self.validate_event_access(event, user_id, 'access')

    def validate_event_ownership(self, event, user_id):
        """Legacy validation method - use validate_owner_access instead"""
        if not self.is_event_owner(event, user_id):
            logger.warning(f'User {user_id} tried to access event {event.id} without ownership')
            raise EventPermissionError(action='ownership', event_id=str(event.event_uuid))

    # =============================================================================
    # PERMISSION CHECKING (boolean returns)
    # =============================================================================

    def is_event_owner(self, event, user_id):
        """Check if user is event owner via EventParticipant"""
        if not event or not user_id:
            return False
        participation = self.participant_dal.get_user_participation_by_id(event, user_id)
        return participation and participation.role == EventParticipant.Role.OWNER

    def is_event_guest(self, event, user_id):
        """Check if user is event guest"""
        if not event or not user_id:
            return False
        return self.participant_dal.is_user_participant_by_id(event, user_id)

    def has_event_access(self, event, user_id):
        """Check if user has any access to event (owner, guest, or public)"""
        if not event:
            return False

        if event.is_public:
            return True

        if not user_id:
            return False

        return self.is_event_owner(event, user_id) or self.is_event_guest(event, user_id)

    def can_modify_event(self, event, user_id):
        """Check if user can modify event (owner + not past date)"""
        try:
            self.validate_owner_access(event, user_id)

            from django.utils import timezone

            if event.date < timezone.now().date():
                logger.warning(f'Event {event.id} modification attempted after event date')
                return False

            return True

        except (EventPermissionError, PermissionError):
            return False

    def can_delete_event(self, event, user_id):
        """Check if user can delete event (owner only)"""
        try:
            self.validate_owner_access(event, user_id)
            return True
        except (EventPermissionError, PermissionError):
            return False

    def can_access_file(self, event, user_id, s3_key):
        """Check if user can access file (owner/guest + key validation)"""
        try:
            self.validate_guest_or_owner_access(event, user_id)

            if hasattr(event, 'event_uuid') and str(event.event_uuid) not in s3_key:
                logger.warning(f'S3 key {s3_key} does not belong to event {event.id}')
                return False

            return True

        except (EventPermissionError, PermissionError):
            return False

    # =============================================================================
    # PERMISSION UTILITIES
    # =============================================================================

    def get_user_event_permissions(self, event, user_id):
        """Get complete permission matrix for user and event"""
        permissions = {
            'is_owner': False,
            'is_guest': False,
            'can_access': False,
            'can_modify': False,
            'can_delete': False,
            'can_upload_files': False,
            'can_download_files': False,
            'can_delete_files': False,
        }

        try:
            permissions['is_owner'] = self.is_event_owner(event, user_id)
            permissions['is_guest'] = self.is_event_guest(event, user_id)
            permissions['can_access'] = permissions['is_owner'] or permissions['is_guest'] or event.is_public

            if permissions['can_access']:
                permissions['can_modify'] = permissions['is_owner']
                permissions['can_delete'] = permissions['is_owner']
                permissions['can_upload_files'] = True
                permissions['can_download_files'] = True
                permissions['can_delete_files'] = permissions['is_owner']

        except Exception as e:
            logger.exception(f'Error getting permissions for user {user_id}, event {event.id}: {e}')

        return permissions

    # =============================================================================
    # NEW METHODS FOR DRF PERMISSIONS (simplified API)
    # =============================================================================

    def can_user_access_event(self, event, user_id: int) -> bool:
        """Check if user can access event"""
        return self.is_event_owner(event, user_id) or self.participant_dal.is_user_participant_by_id(event, user_id)

    def can_user_modify_event(self, event, user_id: int) -> bool:
        """Check if user can modify event"""
        if self.is_event_owner(event, user_id):
            return True

        # Check if user is moderator
        participation = self.participant_dal.get_user_participation_by_id(event, user_id)
        return participation and participation.role == EventParticipant.Role.MODERATOR

    def get_user_participation_in_event(self, event, user) -> Any | None:
        """Get user's participation in event"""
        return self.participant_dal.get_user_participation(event, user)

    # =============================================================================
    # INTERNAL HELPERS
    # =============================================================================
