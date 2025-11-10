import logging

from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.services.user_service import UserService
from apps.events.serializers import BulkGuestInviteSerializer
from apps.events.serializers import EventCreatedResponseSerializer
from apps.events.serializers import EventCreateSerializer
from apps.events.serializers import EventDetailSerializer
from apps.events.serializers import EventListQuerySerializer
from apps.events.serializers import EventListSerializer
from apps.events.serializers import EventParticipantDetailSerializer
from apps.events.serializers import EventParticipantListSerializer
from apps.events.serializers import EventParticipantRSVPUpdateSerializer
from apps.events.serializers import EventUpdateSerializer
from apps.events.serializers import GuestInviteSerializer
from apps.events.serializers import ParticipantListQuerySerializer
from apps.events.services.event_service import EventService
from apps.shared.base.base_api_view import BaseAPIView

logger = logging.getLogger(__name__)


class BaseEventAPIView(BaseAPIView):
    """Base view for event operations"""

    def get_event_service(self):
        return EventService()

    def get_user_service(self):
        return UserService()


class EventCreateAPIView(BaseEventAPIView):
    """Create new event"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Create new event with automatic owner participation"""
        serializer = EventCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        event = self.get_event_service().create_event(validated_data=serializer.validated_data, user=request.user)

        response_serializer = EventCreatedResponseSerializer(event)

        logger.info(f'Created event {event.event_uuid} for user {request.user.id}')
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class EventListAPIView(BaseEventAPIView):
    """List events for authenticated user"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get paginated list of user's events"""
        query_serializer = EventListQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)

        events_data = self.get_event_service().get_events_list(
            filters=query_serializer.validated_data, user_id=request.user.id
        )

        events_serializer = EventListSerializer(events_data['events'], many=True)

        response_data = {'events': events_serializer.data, 'pagination': events_data['pagination']}

        return Response(response_data, status=status.HTTP_200_OK)


class EventDetailAPIView(BaseEventAPIView):
    """Get event details"""

    permission_classes = [IsAuthenticated]

    def get(self, request, event_uuid):
        """Get detailed event information"""
        event = self.get_event_service().get_event_detail(event_uuid=event_uuid, user_id=request.user.id)

        serializer = EventDetailSerializer(event)
        return Response(serializer.data, status=status.HTTP_200_OK)


class EventUpdateAPIView(BaseEventAPIView):
    """Update event"""

    permission_classes = [IsAuthenticated]

    def put(self, request, event_uuid):
        """Update existing event"""
        data_serializer = EventUpdateSerializer(data=request.data)
        data_serializer.is_valid(raise_exception=True)

        event = self.get_event_service().update_event(
            event_uuid=str(event_uuid),
            validated_data=data_serializer.validated_data,
            user_id=request.user.id,
        )

        serializer = EventDetailSerializer(event)

        logger.info(f'Updated event {event.event_uuid} by user {request.user.id}')
        return Response(serializer.data, status=status.HTTP_200_OK)


class EventDeleteAPIView(BaseEventAPIView):
    """Delete event"""

    permission_classes = [IsAuthenticated]

    def delete(self, request, event_uuid):
        """Delete existing event"""
        self.get_event_service().delete_event(
            event_uuid=str(event_uuid), user_id=request.user.id
        )

        logger.info(f"Deleted event {event_uuid} by user {request.user.id}")
        return Response({'message': 'Event deleted successfully'}, status=status.HTTP_200_OK)


# =============================================================================
# EVENT PARTICIPANT OPERATIONS
# =============================================================================


class EventParticipantListAPIView(BaseEventAPIView):
    """List event participants"""

    permission_classes = [IsAuthenticated]

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

        return Response({'participants': serializer.data, 'count': len(participants)}, status=status.HTTP_200_OK)


class EventParticipantDetailAPIView(BaseEventAPIView):
    """Get participant details"""

    permission_classes = [IsAuthenticated]

    def get(self, request, event_uuid, participant_id):
        """Get detailed participant information"""
        participants = self.get_event_service().get_event_participants(
            event_uuid=event_uuid, requesting_user_id=request.user.id
        )

        participant = next((p for p in participants if p.id == participant_id), None)
        if not participant:
            raise NotFound('Participant not found')

        serializer = EventParticipantDetailSerializer(participant)
        return Response(serializer.data, status=status.HTTP_200_OK)


class EventParticipantRSVPUpdateAPIView(BaseEventAPIView):
    """Update participant RSVP status"""

    permission_classes = [IsAuthenticated]

    def patch(self, request, event_uuid, participant_id):
        """Update RSVP status for participant"""
        serializer = EventParticipantRSVPUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Get participants to find the user
        participants = self.get_event_service().get_event_participants(
            event_uuid=event_uuid, requesting_user_id=request.user.id
        )

        participant = next((p for p in participants if p.id == participant_id), None)
        if not participant:
            raise NotFound('Participant not found')

        updated_participation = self.get_event_service().update_participant_rsvp(
            event_uuid=event_uuid,
            user=participant.user,
            rsvp_status=serializer.validated_data['rsvp_status'],
            requesting_user_id=request.user.id,
        )

        response_serializer = EventParticipantDetailSerializer(updated_participation)

        logger.info(f'Updated RSVP for participant {participant.user.id} ' f'in event {event_uuid}')
        return Response(response_serializer.data, status=status.HTTP_200_OK)


# invitation
class EventGuestInviteAPIView(BaseEventAPIView):
    """Invite guest to event"""

    permission_classes = [IsAuthenticated]

    def post(self, request, event_uuid):
        """Invite a guest user to the event"""
        serializer = GuestInviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        guest_user, participation = self.get_event_service().invite_guest_to_event(
            event_uuid=event_uuid,
            guest_name=serializer.validated_data['guest_name'],
            guest_email=serializer.validated_data.get('guest_email', ''),
            requesting_user_id=request.user.id,
            user_service=self.get_user_service(),
        )

        response_serializer = EventParticipantDetailSerializer(participation)

        logger.info(f'Invited guest {guest_user.guest_name} to event {event_uuid}')
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class EventBulkGuestInviteAPIView(BaseEventAPIView):
    """Invite multiple guests to event"""

    permission_classes = [IsAuthenticated]

    def post(self, request, event_uuid):
        """Invite multiple guests to the event"""
        serializer = BulkGuestInviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        invited_participants = []
        failed_invitations = []

        for guest_data in serializer.validated_data['guests']:
            try:
                guest_user, participation = self.get_event_service().invite_guest_to_event(
                    event_uuid=event_uuid,
                    guest_name=guest_data['guest_name'],
                    guest_email=guest_data.get('guest_email', ''),
                    requesting_user_id=request.user.id,
                    user_service=self.get_user_service(),
                )

                invited_participants.append(participation)

            except Exception as e:
                failed_invitations.append({'guest_name': guest_data['guest_name'], 'error': str(e)})

        success_serializer = EventParticipantListSerializer(invited_participants, many=True)

        response_data = {
            'invited_participants': success_serializer.data,
            'successful_count': len(invited_participants),
            'failed_count': len(failed_invitations),
            'failed_invitations': failed_invitations,
        }

        logger.info(f'Bulk invited {len(invited_participants)} guests to event {event_uuid}')
        return Response(response_data, status=status.HTTP_200_OK)


# =============================================================================
# USER RSVP OPERATIONS
# =============================================================================


class MyEventRSVPAPIView(BaseEventAPIView):
    """User's own RSVP management"""

    permission_classes = [IsAuthenticated]

    def get(self, request, event_uuid):
        """Get current user's RSVP status for event"""
        event = self.get_event_service().get_event_detail(event_uuid=event_uuid, user_id=request.user.id)

        participation = self.get_event_service().get_user_participation_in_event(event, request.user)
        if not participation:
            return Response({'message': 'You are not a participant in this event'}, status=status.HTTP_404_NOT_FOUND)

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
