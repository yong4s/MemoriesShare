import logging
from functools import cached_property

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.events.exceptions import EventPermissionError
from apps.events.exceptions import ParticipantNotFoundError
from apps.events.serializers import BulkGuestInviteSerializer
from apps.events.serializers import EventParticipantDetailSerializer
from apps.events.serializers import EventParticipantListSerializer
from apps.events.serializers import EventParticipantRSVPUpdateSerializer
from apps.events.serializers import GuestInviteSerializer
from apps.events.serializers import ParticipantListQuerySerializer
from apps.events.views.base import BaseEventAPIView
from apps.shared.container import get_container
from apps.shared.utils.redact import redact_secrets

logger = logging.getLogger(__name__)


@extend_schema(tags=['Event Participants'])
class EventParticipantListAPIView(BaseEventAPIView):
    """RESTful participants collection - GET for list, POST for invite"""

    permission_classes = [IsAuthenticated]

    @cached_property
    def event_service(self):
        return get_container().event_service()

    @cached_property
    def user_service(self):
        return get_container().user_service()

    def get(self, request, event_uuid):
        query_serializer = ParticipantListQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)

        participants = self.event_service.get_event_participants(
            event_uuid=event_uuid,
            requesting_user_id=request.user.id,
            role_filter=query_serializer.validated_data.get('role'),
            rsvp_filter=query_serializer.validated_data.get('rsvp_status'),
        )

        serializer = EventParticipantListSerializer(participants, many=True)

        return Response(
            {'participants': serializer.data, 'count': len(participants)},
            status=status.HTTP_200_OK,
        )

    def post(self, request, event_uuid):
        # Permission check is enforced inside EventService.add_participant_to_event()
        # via requesting_user_id — validates modify access for non-invite-token requests.
        if isinstance(request.data, list):
            return self._handle_bulk_invite(request, event_uuid)
        return self._handle_single_invite(request, event_uuid)

    def _resolve_invitee(self, guest_name: str, guest_email: str):
        """Find an existing CustomUser by email or create a new guest one.

        - **Existing registered user** → return them. The owner-initiated invite
          will create a participant with PENDING RSVP; the user gets an email
          and decides whether to accept. We do NOT call ``create_guest_user``
          for registered emails (it raises ``GuestInviteRegisteredConflictError``
          to prevent silent attach via guest pathways).
        - **Existing guest user** → reuse the row.
        - **No user yet** → create a fresh guest.
        """
        existing = self.user_service.get_user_by_email(guest_email, registered_only=False)
        if existing:
            return existing
        return self.user_service.create_guest_user(guest_name=guest_name, guest_email=guest_email)

    def _handle_single_invite(self, request, event_uuid):
        serializer = GuestInviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        invitee = self._resolve_invitee(
            guest_name=serializer.validated_data['guest_name'],
            guest_email=serializer.validated_data['guest_email'],
        )

        participation = self.event_service.add_participant_to_event(
            event_uuid=event_uuid,
            user=invitee,
            role='GUEST',
            guest_name=serializer.validated_data['guest_name'],
            guest_email=serializer.validated_data['guest_email'],
            requesting_user_id=request.user.id,
        )

        response_serializer = EventParticipantDetailSerializer(participation)
        logger.info(f'Invited {invitee.email or invitee.guest_name} to event {event_uuid}')
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def _handle_bulk_invite(self, request, event_uuid):
        serializer = BulkGuestInviteSerializer(data={'guests': request.data})
        serializer.is_valid(raise_exception=True)

        invited_participants = []
        failed_invitations = []

        for guest_data in serializer.validated_data['guests']:
            try:
                invitee = self._resolve_invitee(
                    guest_name=guest_data['guest_name'],
                    guest_email=guest_data['guest_email'],
                )

                participation = self.event_service.add_participant_to_event(
                    event_uuid=event_uuid,
                    user=invitee,
                    role='GUEST',
                    guest_name=guest_data['guest_name'],
                    guest_email=guest_data['guest_email'],
                    requesting_user_id=request.user.id,
                )
                invited_participants.append(participation)
            except Exception as e:
                error_code = getattr(e, 'error_code', type(e).__name__)
                failed_invitations.append({
                    'guest_name': guest_data['guest_name'],
                    'error_code': error_code,
                })
                logger.warning(
                    'Guest invitation failed for %s: code=%s detail=%s',
                    guest_data['guest_name'],
                    error_code,
                    redact_secrets(str(e)),
                )

        success_serializer = EventParticipantListSerializer(invited_participants, many=True)

        response_data = {
            'invited_participants': success_serializer.data,
            'successful_count': len(invited_participants),
            'failed_count': len(failed_invitations),
            'failed_invitations': failed_invitations,
        }

        if invited_participants and not failed_invitations:
            status_code = status.HTTP_201_CREATED
            logger.info(f'Bulk invited all {len(invited_participants)} guests to event {event_uuid}')
        elif invited_participants:
            status_code = status.HTTP_207_MULTI_STATUS
            total_guests = len(invited_participants) + len(failed_invitations)
            logger.info(f'Bulk invited {len(invited_participants)}/{total_guests} guests to event {event_uuid}')
        else:
            status_code = status.HTTP_400_BAD_REQUEST
            logger.warning(f'Failed to invite any guests to event {event_uuid}')

        return Response(response_data, status=status_code)


@extend_schema(tags=['Event Participants'])
class EventParticipantAPIView(BaseEventAPIView):
    """RESTful participant resource - GET for details, PATCH for RSVP updates"""

    permission_classes = [IsAuthenticated]

    @cached_property
    def event_service(self):
        return get_container().event_service()

    def get(self, request, event_uuid, participant_id):
        event = self.event_service.dal.get_event_by_uuid_with_participants(event_uuid)
        self.event_service.permission_service.validate_participant_or_owner_access(event, request.user.id)
        participant = self.event_service.participant_dal.get_participant_by_pk(event, participant_id)
        serializer = EventParticipantDetailSerializer(participant)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, event_uuid, participant_id):
        serializer = EventParticipantRSVPUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        event = self.event_service.dal.get_event_by_uuid_with_participants(event_uuid)
        self.event_service.permission_service.validate_participant_or_owner_access(event, request.user.id)
        participant = self.event_service.participant_dal.get_participant_by_pk(event, participant_id)

        if participant.user_id != request.user.id and not self.event_service.permission_service.can_user_modify_event(
            event, request.user.id
        ):
            raise EventPermissionError(action='rsvp_update', event_id=str(event_uuid))

        updated_participation = self.event_service.update_participant_rsvp(
            event_uuid=event_uuid,
            user=participant.user,
            rsvp_status=serializer.validated_data['rsvp_status'],
            requesting_user_id=request.user.id,
        )

        response_serializer = EventParticipantDetailSerializer(updated_participation)

        logger.info(f'Updated RSVP for participant {participant.user.id} in event {event_uuid}')
        return Response(response_serializer.data, status=status.HTTP_200_OK)


@extend_schema(tags=['Event Participants'])
class MyEventRSVPAPIView(BaseEventAPIView):
    """User's own RSVP management"""

    permission_classes = [IsAuthenticated]

    @cached_property
    def event_service(self):
        return get_container().event_service()

    def get(self, request, event_uuid):
        """Get current user's RSVP status for event"""
        event = self.event_service.get_event_detail(event_uuid=event_uuid, user_id=request.user.id)

        try:
            participation = self.event_service.participant_dal.get_user_participation(event, request.user)
        except ParticipantNotFoundError:
            return Response(
                {'message': 'You are not a participant in this event'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = EventParticipantDetailSerializer(participation)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, event_uuid):
        """Update current user's RSVP status"""
        serializer = EventParticipantRSVPUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated_participation = self.event_service.update_participant_rsvp(
            event_uuid=event_uuid,
            user=request.user,
            rsvp_status=serializer.validated_data['rsvp_status'],
            requesting_user_id=request.user.id,
        )

        response_serializer = EventParticipantDetailSerializer(updated_participation)

        logger.info(f'User {request.user.id} updated own RSVP for event {event_uuid}')
        return Response(response_serializer.data, status=status.HTTP_200_OK)
