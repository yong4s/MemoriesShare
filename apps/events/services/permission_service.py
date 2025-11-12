import logging
from typing import Any

from rest_framework.exceptions import PermissionDenied

from apps.accounts.models.custom_user import CustomUser
from apps.accounts.services import UserService
from apps.events.dal.event_dal import EventDAL
from apps.events.models.event import Event
from apps.events.models.event_participant import EventParticipant
from apps.shared.interfaces.permission_interface import IPermissionValidator

logger = logging.getLogger(__name__)


class EventPermissionService(IPermissionValidator):
    """Service for event permission checking and validation"""

    # Role-Based Access Control Matrix
    ROLE_PERMISSIONS = {
        'OWNER': {
            'event.read', 'event.write', 'event.delete',
            'participants.read', 'participants.write', 'participants.delete',
            'files.read', 'files.write', 'files.delete',
            'rsvp.read', 'rsvp.write_any'
        },
        'MODERATOR': {
            'event.read', 'event.write',
            'participants.read', 'participants.write',
            'files.read', 'files.write',
            'rsvp.read', 'rsvp.write_any'
        },
        'GUEST': {
            'event.read',
            'participants.read',
            'files.read', 'files.write',
            'rsvp.read', 'rsvp.write_own'
        }
    }

    def __init__(self, dal: EventDAL | None = None, user_service: UserService | None = None) -> None:
        self.dal = dal or EventDAL()
        self.user_service = user_service or UserService()

    # =============================================================================
    # PERMISSION VALIDATION (main methods)
    # =============================================================================

    def validate_event_access(self, event: Any, user_id: int, required_permission: str = 'access') -> bool:
        """Validate event access"""
        if not user_id:
            logger.warning('Access attempt without user ID')
            raise PermissionDenied('User authentication required')

        has_permission = self._check_permission(event, user_id, required_permission)

        if not has_permission:
            logger.warning(
                f'Permission denied for user {user_id}, event {event.event_uuid}, permission {required_permission}'
            )
            raise PermissionDenied('You do not have permission to access this event')

        return True

    def _check_permission(self, event, user_id, required_permission):
        """Internal permission checking logic"""
        if required_permission == 'owner':
            return self.is_event_owner(event, user_id)
        elif required_permission == 'guest':
            return self.is_event_guest(event, user_id)
        elif required_permission == 'access':
            return self.has_event_access(event, user_id)
        else:
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
            raise PermissionDenied('You do not have permission to access this event')

    # =============================================================================
    # PERMISSION CHECKING (boolean returns)
    # =============================================================================

    def is_event_owner(self, event, user_id):
        """Check if user is event owner"""
        if not event or not user_id:
            return False
        return event.user.pk == user_id

    def is_event_guest(self, event, user_id):
        """Check if user is event guest"""
        if not event or not user_id:
            return False
        return self.dal.is_user_participant(event, user_id)

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

        except PermissionDenied:
            return False

    def can_delete_event(self, event, user_id):
        """Check if user can delete event (owner only)"""
        try:
            self.validate_owner_access(event, user_id)
            return True
        except PermissionDenied:
            return False

    def can_access_file(self, event, user_id, s3_key):
        """Check if user can access file (owner/guest + key validation)"""
        try:
            self.validate_guest_or_owner_access(event, user_id)

            if hasattr(event, 'event_uuid') and str(event.event_uuid) not in s3_key:
                logger.warning(f'S3 key {s3_key} does not belong to event {event.id}')
                return False

            return True

        except PermissionDenied:
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
            logger.error(f'Error getting permissions for user {user_id}, event {event.id}: {e}')

        return permissions

    # =============================================================================
    # RBAC SYSTEM
    # =============================================================================

    def get_user_role_in_event(self, event_id: int, user_id: int) -> str | None:
        """Get user's role in event"""
        try:
            participation = self.dal.get_user_participation_by_id(
                Event.objects.get(id=event_id), user_id
            )
            return participation.role if participation else None
        except Event.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f'Error getting user role: {e}')
            return None

    def has_permission(self, event: Event, user_id: int, permission: str) -> bool:
        """Check if user has specific permission for event"""
        # Public event access
        if permission == 'event.read' and getattr(event, 'is_public', False):
            return True
            
        user_role = self.get_user_role_in_event(event.id, user_id)
        if not user_role:
            return False
            
        return permission in self.ROLE_PERMISSIONS.get(user_role, set())

    def is_moderator(self, event: Event, user_id: int) -> bool:
        """Check if user is moderator in event"""
        user_role = self.get_user_role_in_event(event.id, user_id)
        return user_role == 'MODERATOR'

    # =============================================================================
    # ENHANCED PERMISSION METHODS
    # =============================================================================

    def can_user_modify_participant_rsvp(self, event: Event, participant_user_id: int, requesting_user_id: int) -> bool:
        """Check if user can modify participant's RSVP status"""
        # Users can always modify their own RSVP
        if requesting_user_id == participant_user_id:
            return self.has_permission(event, requesting_user_id, 'rsvp.write_own')

        # Owners and moderators can modify any RSVP
        return self.has_permission(event, requesting_user_id, 'rsvp.write_any')

    def can_manage_participants(self, event: Event, user_id: int) -> bool:
        """Check if user can add/remove participants"""
        return self.has_permission(event, user_id, 'participants.write')

    def can_modify_event(self, event: Event, user_id: int) -> bool:
        """Check if user can modify event (includes time validation)"""
        if not self.has_permission(event, user_id, 'event.write'):
            return False

        # Check if event is not in the past
        from django.utils import timezone
        if hasattr(event, 'date') and event.date < timezone.now().date():
            logger.warning(f'Event {event.id} modification attempted after event date')
            return False

        return True

    def validate_participant_management(self, event: Event, user_id: int, operation: str) -> bool:
        """Validate participant management operations with detailed logging"""
        if not self.can_manage_participants(event, user_id):
            logger.warning(
                f'User {user_id} attempted {operation} on event {event.event_uuid} without permission'
            )
            raise PermissionDenied(f'You cannot {operation} participants for this event')
        return True

    def validate_rsvp_update(self, event: Event, participant_user_id: int, requesting_user_id: int) -> bool:
        """Validate RSVP update with comprehensive checks"""
        if not self.can_user_modify_participant_rsvp(event, participant_user_id, requesting_user_id):
            logger.warning(
                f'User {requesting_user_id} attempted to modify RSVP for user {participant_user_id} '
                f'in event {event.event_uuid} without permission'
            )
            raise PermissionDenied('You can only update your own RSVP status')
        return True

    def get_user_participation_in_event(self, event: Event, user: CustomUser) -> EventParticipant | None:
        """Get user's participation in event (moved from EventService)"""
        return self.dal.get_user_participation(event, user)

    # =============================================================================
    # ENHANCED VALIDATION METHODS
    # =============================================================================

    def validate_event_modification(self, event: Event, user_id: int) -> bool:
        """Validate event modification with enhanced checks"""
        if not self.can_modify_event(event, user_id):
            logger.warning(f'User {user_id} attempted to modify event {event.event_uuid} without permission')
            raise PermissionDenied('You cannot modify this event')
        return True

    def validate_file_access(self, event: Event, user_id: int, s3_key: str, operation: str = 'read') -> bool:
        """Enhanced file access validation"""
        permission = f'files.{operation}'
        if not self.has_permission(event, user_id, permission):
            logger.warning(
                f'User {user_id} attempted to {operation} file {s3_key} '
                f'in event {event.event_uuid} without permission'
            )
            raise PermissionDenied(f'You cannot {operation} files in this event')

        # Validate S3 key belongs to event
        if hasattr(event, 'event_uuid') and str(event.event_uuid) not in s3_key:
            logger.warning(f'S3 key {s3_key} does not belong to event {event.id}')
            raise PermissionDenied('Invalid file access')

        return True

    # =============================================================================
    # BULK OPERATION PERMISSIONS
    # =============================================================================

    def validate_bulk_operations(self, event: Event, user_id: int, operation_type: str) -> bool:
        """Validate bulk operations like bulk invites, bulk RSVP updates"""
        operation_permissions = {
            'bulk_invite': 'participants.write',
            'bulk_rsvp_update': 'rsvp.write_any',
            'bulk_file_upload': 'files.write'
        }

        required_permission = operation_permissions.get(operation_type)
        if not required_permission:
            logger.error(f'Unknown bulk operation type: {operation_type}')
            raise PermissionDenied('Invalid bulk operation')

        if not self.has_permission(event, user_id, required_permission):
            logger.warning(
                f'User {user_id} attempted {operation_type} on event {event.event_uuid} without permission'
            )
            raise PermissionDenied(f'You cannot perform {operation_type} on this event')

        return True

    # =============================================================================
    # BATCH OPERATIONS FOR PERFORMANCE
    # =============================================================================

    def batch_check_permissions(self, event_ids: list[int], user_id: int, permission: str) -> dict[int, bool]:
        """Batch check permissions for multiple events for performance"""
        results = {}

        # Pre-fetch events and participations in one query
        events = Event.objects.filter(id__in=event_ids).select_related('user')
        participations = EventParticipant.objects.filter(
            event_id__in=event_ids, user_id=user_id
        ).select_related('event')

        # Create participation lookup
        participation_map = {p.event_id: p for p in participations}

        for event in events:
            participation = participation_map.get(event.id)
            user_role = participation.role if participation else None

            if user_role:
                results[event.id] = permission in self.ROLE_PERMISSIONS.get(user_role, set())
            else:
                results[event.id] = getattr(event, 'is_public', False) and permission == 'event.read'

        return results

    def get_user_accessible_events(self, event_ids: list[int], user_id: int) -> list[int]:
        """Get list of event IDs user can access (optimized)"""
        permissions = self.batch_check_permissions(event_ids, user_id, 'event.read')
        return [event_id for event_id, can_access in permissions.items() if can_access]

    # =============================================================================
    # INTERNAL HELPERS
    # =============================================================================
