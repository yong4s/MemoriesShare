"""Event validators for complex validation logic."""

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from apps.accounts.models.custom_user import CustomUser
from apps.events.models.event import Event
from apps.events.models.event_participant import EventParticipant


class EventParticipantValidator:
    """Validator for EventParticipant business rules."""

    def validate_add_participant(self, event: Event, user: CustomUser, role: str):
        """Validate business rules before adding participant."""
        errors = {}

        if role == EventParticipant.Role.OWNER:
            if event.participants_through.filter(role=EventParticipant.Role.OWNER).exists():
                errors['role'] = _('Event can only have one owner')
        if event.max_guests:
            current_count = event.participants_through.count()
            if current_count >= event.max_guests:
                errors['event'] = _('Event has reached maximum capacity')

        if user.is_registered and role == EventParticipant.Role.GUEST:
            errors['role'] = _('Registered users cannot be added as guests')

        if user.is_guest and not user.guest_name:
            errors['guest_name'] = _('Guest users must have a display name')

        if event.participants_through.filter(user=user).exists():
            errors['user'] = _('User is already a participant in this event')

        from django.utils import timezone

        if event.date < timezone.now().date():
            errors['event'] = _('Cannot add participants to past events')

        if errors:
            raise ValidationError(errors)

    def validate_role_change(self, participant: EventParticipant, new_role: str):
        """
        Validate role changes for existing participants.

        Args:
            participant: Existing EventParticipant instance
            new_role: New role to assign

        Raises:
            ValidationError: If role change is invalid
        """
        errors = {}

        # Cannot change from owner role
        if participant.role == EventParticipant.Role.OWNER:
            errors['role'] = _('Cannot change role of event owner')

        # Cannot change to owner if owner already exists
        if new_role == EventParticipant.Role.OWNER:
            if (
                participant.event.participants_through.filter(role=EventParticipant.Role.OWNER)
                .exclude(id=participant.id)
                .exists()
            ):
                errors['role'] = _('Event already has an owner')

        # Registered users cannot become guests
        if participant.user.is_registered and new_role == EventParticipant.Role.GUEST:
            errors['role'] = _('Registered users cannot be guests')

        if errors:
            raise ValidationError(errors)

    def validate_rsvp_change(self, participant: EventParticipant, new_status: str):
        """
        Validate RSVP status changes.

        Args:
            participant: EventParticipant instance
            new_status: New RSVP status

        Raises:
            ValidationError: If RSVP change is invalid
        """
        errors = {}

        from django.utils import timezone

        if participant.event.date < timezone.now().date():
            errors['rsvp_status'] = _('Cannot change RSVP for past events')

        # Event owner must always be attending
        if participant.role == EventParticipant.Role.OWNER and new_status in [
            EventParticipant.RsvpStatus.DECLINED,
            EventParticipant.RsvpStatus.NO_SHOW,
        ]:
            errors['rsvp_status'] = _('Event owner cannot decline attendance')

        # Validate status transitions
        valid_transitions = self._get_valid_rsvp_transitions()
        current_status = participant.rsvp_status

        if current_status in valid_transitions and new_status not in valid_transitions[current_status]:
            errors['rsvp_status'] = _(f'Cannot change RSVP from {current_status} to {new_status}')

        if errors:
            raise ValidationError(errors)

    def validate_guest_data(self, participant: EventParticipant, guest_data: dict):
        """
        Validate guest-specific data updates.

        Args:
            participant: EventParticipant instance
            guest_data: Dictionary with guest data

        Raises:
            ValidationError: If guest data is invalid
        """
        errors = {}

        # Only guest users can have guest data
        if not participant.user.is_guest:
            errors['user'] = _('Cannot set guest data for registered users')

        # Validate guest name
        if 'guest_name' in guest_data:
            guest_name = guest_data['guest_name']
            if not guest_name or len(guest_name.strip()) < 2:
                errors['guest_name'] = _('Guest name must be at least 2 characters')

        # Validate guest email format
        if 'guest_email' in guest_data:
            guest_email = guest_data['guest_email']
            if guest_email:  # Email is optional for guests
                from django.core.validators import validate_email

                try:
                    validate_email(guest_email)
                except ValidationError:
                    errors['guest_email'] = _('Invalid email format')

        # Validate phone number format
        if 'guest_phone' in guest_data:
            guest_phone = guest_data['guest_phone']
            if guest_phone and not self._validate_phone_format(guest_phone):
                errors['guest_phone'] = _('Invalid phone number format')

        if errors:
            raise ValidationError(errors)

    def validate_invitation_data(self, event: Event, invitation_data: dict):
        """
        Validate invitation data before sending.

        Args:
            event: Event instance
            invitation_data: Dictionary with invitation data

        Raises:
            ValidationError: If invitation data is invalid
        """
        errors = {}

        if event.date < timezone.now().date():
            errors['event'] = _('Cannot send invitations for past events')

        # Validate invitation token if provided
        if 'invite_token' in invitation_data:
            token = invitation_data['invite_token']
            if not token or len(token) < 16:
                errors['invite_token'] = _('Invitation token must be at least 16 characters')

        # Validate join method
        if 'join_method' in invitation_data:
            valid_methods = ['direct', 'invitation', 'qr_code', 'link']
            if invitation_data['join_method'] not in valid_methods:
                errors['join_method'] = _('Invalid join method')

        if errors:
            raise ValidationError(errors)

    def _get_valid_rsvp_transitions(self) -> dict:
        """
        Get valid RSVP status transitions.

        Returns:
            dict: Mapping of current status to allowed next statuses
        """
        return {
            EventParticipant.RsvpStatus.PENDING: [
                EventParticipant.RsvpStatus.ACCEPTED,
                EventParticipant.RsvpStatus.DECLINED,
                EventParticipant.RsvpStatus.TENTATIVE,
                EventParticipant.RsvpStatus.MAYBE,
                EventParticipant.RsvpStatus.WAITLISTED,
            ],
            EventParticipant.RsvpStatus.ACCEPTED: [
                EventParticipant.RsvpStatus.DECLINED,
                EventParticipant.RsvpStatus.TENTATIVE,
                EventParticipant.RsvpStatus.CONFIRMED_PLUS_ONE,
                EventParticipant.RsvpStatus.NO_SHOW,
            ],
            EventParticipant.RsvpStatus.DECLINED: [
                EventParticipant.RsvpStatus.ACCEPTED,
                EventParticipant.RsvpStatus.TENTATIVE,
                EventParticipant.RsvpStatus.MAYBE,
                EventParticipant.RsvpStatus.DECLINED_WITH_REGRET,
            ],
            EventParticipant.RsvpStatus.TENTATIVE: [
                EventParticipant.RsvpStatus.ACCEPTED,
                EventParticipant.RsvpStatus.DECLINED,
                EventParticipant.RsvpStatus.MAYBE,
            ],
            EventParticipant.RsvpStatus.MAYBE: [
                EventParticipant.RsvpStatus.ACCEPTED,
                EventParticipant.RsvpStatus.DECLINED,
                EventParticipant.RsvpStatus.TENTATIVE,
            ],
        }

    def _validate_phone_format(self, phone: str) -> bool:
        """
        Validate phone number format.

        Args:
            phone: Phone number string

        Returns:
            bool: True if valid format
        """
        import re

        # Simple phone validation - can be enhanced
        pattern = r'^\+?[\d\s\-\(\)]{10,15}$'
        return bool(re.match(pattern, phone.strip()))
