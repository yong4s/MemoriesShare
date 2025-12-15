import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.services.user_service import UserService
from apps.events.permissions import CanAccessEvent
from apps.events.permissions import EventPermissionMixin
from apps.events.permissions import IsEventOwner
from apps.events.serializers import EventCreatedResponseSerializer
from apps.events.serializers import EventCreateSerializer
from apps.events.serializers import EventDetailSerializer
from apps.events.serializers import EventListQuerySerializer
from apps.events.serializers import EventListSerializer
from apps.events.serializers import EventUpdateSerializer
from apps.shared.base.base_api_view import BaseAPIView
from apps.shared.container import get_event_service

logger = logging.getLogger(__name__)


class BaseEventAPIView(BaseAPIView):
    """Base view for event operations"""

    _event_service = None
    _user_service = None

    def get_event_service(self):
        if self._event_service is None:
            self._event_service = get_event_service()
        return self._event_service

    def get_user_service(self):
        if self._user_service is None:
            self._user_service = UserService()
        return self._user_service


@extend_schema(tags=["Events"])
class EventCreateAPIView(BaseEventAPIView):
    """Create new event"""

    permission_classes = [IsAuthenticated]
    serializer_class = EventCreateSerializer

    def post(self, request):
        """Create new event with automatic owner participation"""
        serializer = EventCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        event = self.get_event_service().create_event(
            validated_data=serializer.validated_data, user=request.user
        )

        response_serializer = EventCreatedResponseSerializer(event)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Events"])
class EventListAPIView(BaseEventAPIView):
    """List all available events"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get list of all events with optional filtering"""
        query_serializer = EventListQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)

        events_data = self.get_event_service().get_events_list(
            filters=query_serializer.validated_data, user=request.user
        )

        events_serializer = EventListSerializer(events_data["events"], many=True)

        response_data = {
            "events": events_serializer.data,
            "pagination": events_data["pagination"],
        }
        return Response(response_data, status=status.HTTP_200_OK)


@extend_schema(tags=["Events"])
class MyEventsAPIView(BaseEventAPIView):
    """Get current user's events (owned and participating)"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get events where current user is owner or participant"""
        query_serializer = EventListQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)

        # Force owned_only to True for this endpoint
        filters = query_serializer.validated_data.copy()
        filters["owned_only"] = True

        events_data = self.get_event_service().get_events_list(
            filters=filters, user=request.user
        )

        events_serializer = EventListSerializer(events_data["events"], many=True)

        response_data = {
            "events": events_serializer.data,
            "pagination": events_data["pagination"],
        }
        return Response(response_data, status=status.HTTP_200_OK)


@extend_schema(tags=["Events"])
class EventDetailAPIView(BaseEventAPIView, EventPermissionMixin):
    """Get event details"""

    permission_classes = [IsAuthenticated, CanAccessEvent]

    def get(self, request, event_uuid):
        """Get detailed event information"""
        event = self.get_event_service().get_event_detail(
            event_uuid=event_uuid, user_id=request.user.id
        )
        serializer = EventDetailSerializer(event)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(tags=["Events"])
class EventUpdateAPIView(BaseEventAPIView, EventPermissionMixin):

    permission_classes = [IsAuthenticated, IsEventOwner]

    def put(self, request, event_uuid):
        """Update event information"""
        serializer = EventUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        event = self.get_event_service().update_event(
            event_uuid=event_uuid,
            validated_data=serializer.validated_data,
            user=request.user,
        )

        response_serializer = EventDetailSerializer(event)
        return Response(response_serializer.data, status=status.HTTP_200_OK)


@extend_schema(tags=["Events"])
class EventDeleteAPIView(BaseEventAPIView, EventPermissionMixin):

    permission_classes = [IsAuthenticated, IsEventOwner]

    def delete(self, request, event_uuid):
        """Delete event and all associated data"""
        self.get_event_service().delete_event(
            event_uuid=event_uuid, user_id=request.user.id
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
