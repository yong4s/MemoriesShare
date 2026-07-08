from functools import cached_property

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.events.serializers import EventListSerializer
from apps.events.views.base import BaseEventAPIView
from apps.shared.container import get_container


@extend_schema(tags=['Event Analytics'])
class EventAnalyticsAPIView(BaseEventAPIView):
    """Event analytics and statistics"""

    permission_classes = [IsAuthenticated]

    @cached_property
    def event_service(self):
        return get_container().event_service()

    @cached_property
    def analytics_service(self):
        return get_container().analytics_service()

    def get(self, request, event_uuid):
        """Get event analytics and statistics"""
        event = self.event_service.get_event_detail(event_uuid=event_uuid, user_id=request.user.id)

        statistics = self.analytics_service.get_event_statistics(event)

        participants = self.event_service.get_event_participants(
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
                },
            },
            'total_participants': len(participants),
        }

        return Response(response_data, status=status.HTTP_200_OK)


@extend_schema(tags=['Event Analytics'])
class UserEventAnalyticsAPIView(BaseEventAPIView):
    """User's event analytics"""

    permission_classes = [IsAuthenticated]

    @cached_property
    def analytics_service(self):
        return get_container().analytics_service()

    def get(self, request):
        """Get user's event participation analytics"""
        data = self.analytics_service.get_user_event_analytics(request.user.id)
        user_stats = data['user_statistics']
        recent_events = data['recent_events']
        upcoming_events = data['upcoming_events']

        response_data = {
            'user_statistics': user_stats,
            'recent_events': EventListSerializer(recent_events, many=True).data,
            'upcoming_events': EventListSerializer(upcoming_events, many=True).data,
            'summary': {
                'total_events': user_stats.get('total_events', 0),
                'owned_events': user_stats.get('owned_events', 0),
                'upcoming_count': len(upcoming_events),
                'recent_count': len(recent_events),
            },
        }

        return Response(response_data, status=status.HTTP_200_OK)
