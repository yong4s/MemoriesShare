import logging
from functools import cached_property

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.events.serializers import EventPublicInviteIssueResponseSerializer
from apps.events.serializers import EventPublicInviteIssueSerializer
from apps.events.serializers import EventPublicInviteJoinResponseSerializer
from apps.events.serializers import EventPublicInviteJoinSerializer
from apps.events.views.base import BaseEventAPIView
from apps.shared.container import get_container

logger = logging.getLogger(__name__)


@extend_schema(tags=['Event Invitations'])
class EventPublicInviteLinkAPIView(BaseEventAPIView):
    """Issue shared invite URL for frontend-side QR rendering."""

    permission_classes = [IsAuthenticated]

    @cached_property
    def invite_link_service(self):
        return get_container().invite_link_service()

    def post(self, request, event_uuid):
        serializer = EventPublicInviteIssueSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)

        result = self.invite_link_service.issue_public_invite_link(
            event_uuid=str(event_uuid),
            requested_by_user_id=request.user.id,
            ttl_hours=serializer.validated_data['ttl_hours'],
            max_uses=serializer.validated_data['max_uses'],
        )

        response_serializer = EventPublicInviteIssueResponseSerializer(result)
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, event_uuid):
        """Revoke the active public invite link — rotates token + forces expiry."""
        self.invite_link_service.revoke_public_invite_link(
            event_uuid=str(event_uuid),
            requested_by_user_id=request.user.id,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=['Event Invitations'])
class EventPublicInviteJoinAPIView(BaseEventAPIView):
    """Consume signed invite token and join event as authenticated user."""

    permission_classes = [IsAuthenticated]

    @cached_property
    def invite_link_service(self):
        return get_container().invite_link_service()

    def post(self, request):
        serializer = EventPublicInviteJoinSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = self.invite_link_service.consume_public_invite_link(
            signed_token=serializer.validated_data['invite_token'],
            authenticated_user_id=request.user.id,
        )
        response_serializer = EventPublicInviteJoinResponseSerializer(result)
        status_code = status.HTTP_200_OK if result.get('already_joined') else status.HTTP_201_CREATED
        return Response(response_serializer.data, status=status_code)
