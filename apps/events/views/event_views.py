import logging
from functools import cached_property

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.events.serializers import EventCreatedResponseSerializer
from apps.events.serializers import EventCreateSerializer
from apps.events.serializers import EventDetailSerializer
from apps.events.serializers import EventListQuerySerializer
from apps.events.serializers import EventListSerializer
from apps.events.serializers import EventUpdateSerializer
from apps.events.views.base import BaseEventAPIView
from apps.shared.container import get_container

logger = logging.getLogger(__name__)


@extend_schema(tags=['Events'])
class EventListAPIView(BaseEventAPIView):
    """RESTful Events collection - GET for list, POST for create"""

    permission_classes = [IsAuthenticated]

    @cached_property
    def event_service(self):
        return get_container().event_service()

    def get(self, request):
        query_serializer = EventListQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)

        events_data = self.event_service.get_events_list(filters=query_serializer.validated_data, user=request.user)

        events_serializer = EventListSerializer(events_data['events'], many=True)

        response_data = {
            'events': events_serializer.data,
            'pagination': events_data['pagination'],
        }
        return Response(response_data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = EventCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        event = self.event_service.create_event(validated_data=serializer.validated_data, user=request.user)

        response_serializer = EventCreatedResponseSerializer(event)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(tags=['Events'])
class EventAPIView(BaseEventAPIView):
    permission_classes = [IsAuthenticated]

    @cached_property
    def event_service(self):
        return get_container().event_service()

    def get(self, request, event_uuid):
        event = self.event_service.get_event_detail(event_uuid=event_uuid, user_id=request.user.id)
        serializer = EventDetailSerializer(event)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, event_uuid):
        serializer = EventUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        event = self.event_service.update_event(
            event_uuid=event_uuid,
            validated_data=serializer.validated_data,
            user=request.user,
        )

        response_serializer = EventDetailSerializer(event)
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, event_uuid):
        self.event_service.delete_event(event_uuid=event_uuid, user_id=request.user.id)
        return Response(status=status.HTTP_204_NO_CONTENT)
