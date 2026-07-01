"""Event validators for complex validation logic."""

from django.utils import timezone

from apps.events.exceptions import EventValidationError
from apps.events.models.event_participant import EventParticipant


class EventParticipantValidator:
    """Validator for EventParticipant business rules."""

    def validate_rsvp_change(self, participant: EventParticipant, new_status: str):
        """Validate an RSVP status change.

        Raises:
            EventValidationError: domain exception (mapped to HTTP 400) if the change is invalid.
        """
        errors = []

        if participant.event.date < timezone.now().date():
            errors.append('Cannot change RSVP for past events')

        # Event owner must always be attending
        if participant.role == EventParticipant.Role.OWNER and new_status in {
            EventParticipant.RsvpStatus.DECLINED,
            EventParticipant.RsvpStatus.NO_SHOW,
        }:
            errors.append('Event owner cannot decline attendance')

        # Validate status transitions
        valid_transitions = self._get_valid_rsvp_transitions()
        current_status = participant.rsvp_status

        if current_status in valid_transitions and new_status not in valid_transitions[current_status]:
            errors.append(f'Cannot change RSVP from {current_status} to {new_status}')

        if errors:
            raise EventValidationError('; '.join(errors))

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
