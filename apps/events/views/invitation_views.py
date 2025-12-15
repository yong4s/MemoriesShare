import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.events.permissions import EventPermissionMixin
from apps.events.permissions import IsEventOwnerOrModerator
from apps.events.serializers import BulkGuestInviteSerializer
from apps.events.serializers import EventParticipantDetailSerializer
from apps.events.serializers import EventParticipantListSerializer
from apps.events.serializers import GuestInviteSerializer

from .event_views import BaseEventAPIView

logger = logging.getLogger(__name__)


@extend_schema(tags=["Event Invitations"])
class EventGuestInviteAPIView(BaseEventAPIView, EventPermissionMixin):
    """Invite guest to event"""

    permission_classes = [IsAuthenticated, IsEventOwnerOrModerator]

    def post(self, request, event_uuid):
        """Invite a guest user to the event"""
        serializer = GuestInviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        guest_user, participation = self.get_event_service().invite_guest_to_event(
            event_uuid=event_uuid,
            guest_name=serializer.validated_data["guest_name"],
            guest_email=serializer.validated_data.get("guest_email", ""),
            requesting_user_id=request.user.id,
            user_service=self.get_user_service(),
        )

        response_serializer = EventParticipantDetailSerializer(participation)

        logger.info(f"Invited guest {guest_user.guest_name} to event {event_uuid}")
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Event Invitations"])
class EventBulkGuestInviteAPIView(BaseEventAPIView, EventPermissionMixin):
    """Invite multiple guests to event"""

    permission_classes = [IsAuthenticated, IsEventOwnerOrModerator]

    def post(self, request, event_uuid):
        """Invite multiple guests to the event"""
        serializer = BulkGuestInviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        invited_participants = []
        failed_invitations = []

        for guest_data in serializer.validated_data["guests"]:
            try:
                (
                    guest_user,
                    participation,
                ) = self.get_event_service().invite_guest_to_event(
                    event_uuid=event_uuid,
                    guest_name=guest_data["guest_name"],
                    guest_email=guest_data.get("guest_email", ""),
                    requesting_user_id=request.user.id,
                    user_service=self.get_user_service(),
                )

                invited_participants.append(participation)
                logger.debug(
                    f'Successfully invited guest {guest_data["guest_name"]} to event {event_uuid}'
                )

            except Exception as e:
                failed_invitations.append(
                    {
                        "guest_name": guest_data["guest_name"],
                        "error_type": getattr(e, "error_code", type(e).__name__),
                        "error": str(e),
                    }
                )
                logger.warning(
                    f'Guest invitation failed for {guest_data["guest_name"]}: {e}'
                )

        success_serializer = EventParticipantListSerializer(
            invited_participants, many=True
        )

        response_data = {
            "invited_participants": success_serializer.data,
            "successful_count": len(invited_participants),
            "failed_count": len(failed_invitations),
            "failed_invitations": failed_invitations,
        }

        if len(invited_participants) > 0 and len(failed_invitations) == 0:
            status_code = status.HTTP_201_CREATED
            logger.info(
                f"Bulk invited all {len(invited_participants)} guests to event {event_uuid}"
            )
        elif len(invited_participants) > 0:
            status_code = status.HTTP_207_MULTI_STATUS
            logger.info(
                f"Bulk invited {len(invited_participants)}/{len(invited_participants)+len(failed_invitations)} guests to event {event_uuid}"
            )
        else:
            status_code = status.HTTP_400_BAD_REQUEST
            logger.warning(f"Failed to invite any guests to event {event_uuid}")

        return Response(response_data, status=status_code)
