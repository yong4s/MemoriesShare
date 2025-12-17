import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.events.permissions import CanAccessEvent
from apps.events.permissions import EventPermissionMixin
from apps.events.permissions import IsEventOwnerOrModerator
from apps.events.permissions import IsEventParticipant
from apps.events.serializers import EventParticipantDetailSerializer
from apps.events.serializers import EventParticipantListSerializer
from apps.events.serializers import EventParticipantRSVPUpdateSerializer
from apps.events.serializers import ParticipantListQuerySerializer
from apps.events.views.event_views import BaseEventAPIView

logger = logging.getLogger(__name__)


@extend_schema(tags=['Event Participants'])
class EventParticipantListAPIView(BaseEventAPIView, EventPermissionMixin):
    """List event participants"""

    permission_classes = [IsAuthenticated, CanAccessEvent]

    def get(self, request, event_uuid):
        """Get list of event participants"""
        query_serializer = ParticipantListQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)

        participants = self.get_event_service().get_event_participants(
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


@extend_schema(tags=['Event Participants'])
class EventParticipantDetailAPIView(BaseEventAPIView, EventPermissionMixin):
    """Get participant details"""

    permission_classes = [IsAuthenticated, CanAccessEvent]

    def get(self, request, event_uuid, participant_id):
        """Get detailed participant information"""
        participants = self.get_event_service().get_event_participants(
            event_uuid=event_uuid, requesting_user_id=request.user.id
        )

        participant = next((p for p in participants if p.id == participant_id), None)
        if not participant:
            msg = 'Participant not found'
            raise NotFound(msg)

        serializer = EventParticipantDetailSerializer(participant)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(tags=['Event Participants'])
class EventParticipantRSVPUpdateAPIView(BaseEventAPIView, EventPermissionMixin):
    """Update participant RSVP status"""

    permission_classes = [IsAuthenticated, IsEventOwnerOrModerator]

    def patch(self, request, event_uuid, participant_id):
        """Update RSVP status for participant"""
        serializer = EventParticipantRSVPUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        participants = self.get_event_service().get_event_participants(
            event_uuid=event_uuid, requesting_user_id=request.user.id
        )

        participant = next((p for p in participants if p.id == participant_id), None)
        if not participant:
            msg = 'Participant not found'
            raise NotFound(msg)

        updated_participation = self.get_event_service().update_participant_rsvp(
            event_uuid=event_uuid,
            user=participant.user,
            rsvp_status=serializer.validated_data['rsvp_status'],
            requesting_user_id=request.user.id,
        )

        response_serializer = EventParticipantDetailSerializer(updated_participation)

        logger.info(f'Updated RSVP for participant {participant.user.id} in event {event_uuid}')
        return Response(response_serializer.data, status=status.HTTP_200_OK)


@extend_schema(tags=['Event Participants'])
class MyEventRSVPAPIView(BaseEventAPIView, EventPermissionMixin):
    """User's own RSVP management"""

    permission_classes = [IsAuthenticated, IsEventParticipant]

    def get(self, request, event_uuid):
        """Get current user's RSVP status for event"""
        event = self.get_event_service().get_event_detail(event_uuid=event_uuid, user_id=request.user.id)

        participation = self.get_event_service().get_user_participation_in_event(event, request.user)
        if not participation:
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

        updated_participation = self.get_event_service().update_participant_rsvp(
            event_uuid=event_uuid,
            user=request.user,
            rsvp_status=serializer.validated_data['rsvp_status'],
            requesting_user_id=request.user.id,
        )

        response_serializer = EventParticipantDetailSerializer(updated_participation)

        logger.info(f'User {request.user.id} updated own RSVP for event {event_uuid}')
        return Response(response_serializer.data, status=status.HTTP_200_OK)
