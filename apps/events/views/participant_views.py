import logging
from functools import cached_property

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.events.exceptions import ParticipantNotFoundError
from apps.events.serializers import BulkGuestInviteSerializer
from apps.events.serializers import EventParticipantDetailSerializer
from apps.events.serializers import EventParticipantListSerializer
from apps.events.serializers import EventParticipantRSVPUpdateSerializer
from apps.events.serializers import GuestInviteSerializer
from apps.events.serializers import ParticipantListQuerySerializer
from apps.events.views.base import BaseEventAPIView
from apps.shared.container import get_container

logger = logging.getLogger(__name__)


@extend_schema(tags=['Event Participants'])
class EventParticipantListAPIView(BaseEventAPIView):
    """RESTful participants collection - GET for list, POST for invite"""

    permission_classes = [IsAuthenticated]

    @cached_property
    def event_service(self):
        return get_container().event_service()

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

    def _handle_single_invite(self, request, event_uuid):
        serializer = GuestInviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        participation = self.event_service.invite_guest(
            event_uuid=event_uuid,
            guest_name=serializer.validated_data['guest_name'],
            guest_email=serializer.validated_data['guest_email'],
            requesting_user_id=request.user.id,
        )

        response_serializer = EventParticipantDetailSerializer(participation)
        logger.info('Invited a guest to event %s', event_uuid)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def _handle_bulk_invite(self, request, event_uuid):
        serializer = BulkGuestInviteSerializer(data={'guests': request.data})
        serializer.is_valid(raise_exception=True)

        result = self.event_service.bulk_invite_guests(
            event_uuid=event_uuid,
            guests=serializer.validated_data['guests'],
            requesting_user_id=request.user.id,
        )
        invited = result['invited']
        failed = result['failed']

        success_serializer = EventParticipantListSerializer(invited, many=True)
        response_data = {
            'invited_participants': success_serializer.data,
            'successful_count': len(invited),
            'failed_count': len(failed),
            'failed_invitations': failed,
        }

        if invited and not failed:
            status_code = status.HTTP_201_CREATED
        elif invited:
            status_code = status.HTTP_207_MULTI_STATUS
        else:
            status_code = status.HTTP_400_BAD_REQUEST

        logger.info('Bulk invite to event %s: %s ok, %s failed', event_uuid, len(invited), len(failed))
        return Response(response_data, status=status_code)


@extend_schema(tags=['Event Participants'])
class EventParticipantAPIView(BaseEventAPIView):
    """RESTful participant resource - GET for details, PATCH for RSVP updates"""

    permission_classes = [IsAuthenticated]

    @cached_property
    def event_service(self):
        return get_container().event_service()

    def get(self, request, event_uuid, participant_id):
        participant = self.event_service.get_participant_detail(
            event_uuid=event_uuid,
            participant_id=participant_id,
            requesting_user_id=request.user.id,
        )
        serializer = EventParticipantDetailSerializer(participant)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, event_uuid, participant_id):
        serializer = EventParticipantRSVPUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated_participation = self.event_service.update_participant_rsvp_by_id(
            event_uuid=event_uuid,
            participant_id=participant_id,
            rsvp_status=serializer.validated_data['rsvp_status'],
            requesting_user_id=request.user.id,
        )

        response_serializer = EventParticipantDetailSerializer(updated_participation)
        logger.info('Updated RSVP for participant %s in event %s', participant_id, event_uuid)
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
