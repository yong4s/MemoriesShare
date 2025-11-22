import logging

from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.services.user_service import UserService
from apps.events.permissions import (
    CanAccessEvent,
    EventPermissionMixin,
    IsEventOwner,
    IsEventOwnerOrModerator,
    IsEventParticipant,
)
from apps.events.serializers import (
    BulkGuestInviteSerializer,
    EventCreatedResponseSerializer,
    EventCreateSerializer,
    EventDetailSerializer,
    EventListQuerySerializer,
    EventListSerializer,
    EventParticipantDetailSerializer,
    EventParticipantListSerializer,
    EventParticipantRSVPUpdateSerializer,
    EventUpdateSerializer,
    GuestInviteSerializer,
    ParticipantListQuerySerializer,
)
from apps.shared.base.base_api_view import BaseAPIView
from apps.shared.container import get_event_service

logger = logging.getLogger(__name__)


class BaseEventAPIView(BaseAPIView):
    """Base view for event operations"""

    def __init__(self, event_service=None, user_service=None, **kwargs):
        super().__init__(**kwargs)
        self._event_service = event_service
        self._user_service = user_service

    def get_event_service(self):
        return self._event_service or get_event_service()

    def get_user_service(self):
        return self._user_service or UserService()


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


class MyEventsAPIView(BaseEventAPIView):
    """List user's owned events"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get paginated list of user's owned events only"""
        query_serializer = EventListQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)

        # Force owned_only to True for this endpoint
        filters = query_serializer.validated_data.copy()
        filters['owned_only'] = True

        events_data = self.get_event_service().get_events_list(
            filters=filters, user_id=request.user.id
        )

        events_serializer = EventListSerializer(events_data['events'], many=True)

        response_data = {'events': events_serializer.data, 'pagination': events_data['pagination']}

        return Response(response_data, status=status.HTTP_200_OK)


class EventDetailAPIView(BaseEventAPIView, EventPermissionMixin):
    """Get event details"""

    permission_classes = [IsAuthenticated, CanAccessEvent]

    def get(self, request, event_uuid):
        """Get detailed event information"""
        event = self.get_event_service().get_event_detail(event_uuid=event_uuid, user_id=request.user.id)

        serializer = EventDetailSerializer(event)
        return Response(serializer.data, status=status.HTTP_200_OK)


class EventUpdateAPIView(BaseEventAPIView, EventPermissionMixin):
    """Update event"""

    permission_classes = [IsAuthenticated, IsEventOwnerOrModerator]

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


class EventDeleteAPIView(BaseEventAPIView, EventPermissionMixin):
    """Delete event"""

    permission_classes = [IsAuthenticated, IsEventOwner]

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

        return Response({'participants': serializer.data, 'count': len(participants)}, status=status.HTTP_200_OK)


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
            raise NotFound('Participant not found')

        serializer = EventParticipantDetailSerializer(participant)
        return Response(serializer.data, status=status.HTTP_200_OK)


class EventParticipantRSVPUpdateAPIView(BaseEventAPIView, EventPermissionMixin):
    """Update participant RSVP status"""

    permission_classes = [IsAuthenticated, IsEventOwnerOrModerator]

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
class EventGuestInviteAPIView(BaseEventAPIView, EventPermissionMixin):
    """Invite guest to event"""

    permission_classes = [IsAuthenticated, IsEventOwnerOrModerator]

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


class EventBulkGuestInviteAPIView(BaseEventAPIView, EventPermissionMixin):
    """Invite multiple guests to event"""

    permission_classes = [IsAuthenticated, IsEventOwnerOrModerator]

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
                logger.debug(f'Successfully invited guest {guest_data["guest_name"]} to event {event_uuid}')

            except Exception as e:
                # All business exceptions are now handled consistently by our global handler
                # Just log the specific guest invitation failure and continue with next guest
                failed_invitations.append({
                    'guest_name': guest_data['guest_name'],
                    'error_type': getattr(e, 'error_code', type(e).__name__),
                    'error': str(e)
                })
                logger.warning(f'Guest invitation failed for {guest_data["guest_name"]}: {e}')

        success_serializer = EventParticipantListSerializer(invited_participants, many=True)

        response_data = {
            'invited_participants': success_serializer.data,
            'successful_count': len(invited_participants),
            'failed_count': len(failed_invitations),
            'failed_invitations': failed_invitations,
        }

        # Use appropriate status code based on results
        if len(invited_participants) > 0 and len(failed_invitations) == 0:
            # All successful
            status_code = status.HTTP_201_CREATED
            logger.info(f'Bulk invited all {len(invited_participants)} guests to event {event_uuid}')
        elif len(invited_participants) > 0:
            # Partial success
            status_code = status.HTTP_207_MULTI_STATUS
            logger.info(f'Bulk invited {len(invited_participants)}/{len(invited_participants)+len(failed_invitations)} guests to event {event_uuid}')
        else:
            # All failed
            status_code = status.HTTP_400_BAD_REQUEST
            logger.warning(f'Failed to invite any guests to event {event_uuid}')

        return Response(response_data, status=status_code)


# =============================================================================
# USER RSVP OPERATIONS
# =============================================================================


class MyEventRSVPAPIView(BaseEventAPIView, EventPermissionMixin):
    """User's own RSVP management"""

    permission_classes = [IsAuthenticated, IsEventParticipant]

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


# =============================================================================
# EVENT ANALYTICS OPERATIONS
# =============================================================================


class EventAnalyticsAPIView(BaseEventAPIView, EventPermissionMixin):
    """Event analytics and statistics"""

    permission_classes = [IsAuthenticated, CanAccessEvent]

    def get(self, request, event_uuid):
        """Get event analytics and statistics"""
        event = self.get_event_service().get_event_detail(event_uuid=event_uuid, user_id=request.user.id)
        
        from apps.events.dal.event_analytics_dal import EventAnalyticsDAL
        analytics_dal = EventAnalyticsDAL()
        
        # Get event statistics
        statistics = analytics_dal.get_event_statistics(event)
        
        # Get participants by role/status breakdowns
        participants = self.get_event_service().get_event_participants(
            event_uuid=event_uuid, requesting_user_id=request.user.id
        )
        
        response_data = {
            'event_uuid': str(event_uuid),
            'event_name': event.event_name,
            'statistics': statistics,
            'participant_breakdown': {
                'by_role': {
                    'owners': statistics.get('owners_count', 0),
                    'moderators': statistics.get('moderators_count', 0),
                    'guests': statistics.get('guests_count', 0),
                },
                'by_rsvp': {
                    'accepted': statistics.get('accepted_count', 0),
                    'pending': statistics.get('pending_count', 0),
                    'declined': statistics.get('declined_count', 0),
                }
            },
            'total_participants': len(participants)
        }
        
        return Response(response_data, status=status.HTTP_200_OK)


class UserEventAnalyticsAPIView(BaseEventAPIView):
    """User's event analytics"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get user's event participation analytics"""
        from apps.events.dal.event_analytics_dal import EventAnalyticsDAL
        analytics_dal = EventAnalyticsDAL()
        
        # Get user participation statistics
        user_stats = analytics_dal.get_user_participation_statistics(request.user.id)
        
        # Get recent events
        recent_events = analytics_dal.get_recent_events(request.user.id, limit=5)
        
        # Get upcoming events
        upcoming_events = analytics_dal.get_upcoming_events(request.user.id, limit=5)
        
        # Serialize events
        from apps.events.serializers import EventListSerializer
        recent_serializer = EventListSerializer(recent_events, many=True)
        upcoming_serializer = EventListSerializer(upcoming_events, many=True)
        
        response_data = {
            'user_statistics': user_stats,
            'recent_events': recent_serializer.data,
            'upcoming_events': upcoming_serializer.data,
            'summary': {
                'total_events': user_stats.get('total_events', 0),
                'owned_events': user_stats.get('owned_events', 0),
                'upcoming_count': len(upcoming_events),
                'recent_count': len(recent_events),
            }
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
