from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.events.dal.event_analytics_dal import EventAnalyticsDAL
from apps.events.permissions import CanAccessEvent
from apps.events.permissions import EventPermissionMixin
from apps.events.serializers import EventListSerializer

from .event_views import BaseEventAPIView


@extend_schema(tags=["Event Analytics"])
class EventAnalyticsAPIView(BaseEventAPIView, EventPermissionMixin):
    """Event analytics and statistics"""

    permission_classes = [IsAuthenticated, CanAccessEvent]

    def get(self, request, event_uuid):
        """Get event analytics and statistics"""
        event = self.get_event_service().get_event_detail(
            event_uuid=event_uuid, user_id=request.user.id
        )

        analytics_dal = EventAnalyticsDAL()

        statistics = analytics_dal.get_event_statistics(event)

        participants = self.get_event_service().get_event_participants(
            event_uuid=event_uuid, requesting_user_id=request.user.id
        )

        response_data = {
            "event_uuid": str(event_uuid),
            "event_name": event.event_name,
            "statistics": statistics,
            "participant_breakdown": {
                "by_role": {
                    "owners": statistics.get("owners_count", 0),
                    "moderators": statistics.get("moderators_count", 0),
                    "guests": statistics.get("guests_count", 0),
                },
                "by_rsvp": {
                    "accepted": statistics.get("accepted_count", 0),
                    "pending": statistics.get("pending_count", 0),
                    "declined": statistics.get("declined_count", 0),
                },
            },
            "total_participants": len(participants),
        }

        return Response(response_data, status=status.HTTP_200_OK)


@extend_schema(tags=["Event Analytics"])
class UserEventAnalyticsAPIView(BaseEventAPIView):
    """User's event analytics"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get user's event participation analytics"""
        analytics_dal = EventAnalyticsDAL()

        user_stats = analytics_dal.get_user_participation_statistics(request.user.id)

        recent_events = analytics_dal.get_recent_events(request.user.id, limit=5)

        upcoming_events = analytics_dal.get_upcoming_events(request.user.id, limit=5)

        recent_serializer = EventListSerializer(recent_events, many=True)
        upcoming_serializer = EventListSerializer(upcoming_events, many=True)

        response_data = {
            "user_statistics": user_stats,
            "recent_events": recent_serializer.data,
            "upcoming_events": upcoming_serializer.data,
            "summary": {
                "total_events": user_stats.get("total_events", 0),
                "owned_events": user_stats.get("owned_events", 0),
                "upcoming_count": len(upcoming_events),
                "recent_count": len(recent_events),
            },
        }

        return Response(response_data, status=status.HTTP_200_OK)
