from django.urls import path

from apps.events.views import EventAnalyticsAPIView
from apps.events.views import EventAPIView
from apps.events.views import EventListAPIView
from apps.events.views import EventParticipantAPIView
from apps.events.views import EventParticipantListAPIView
from apps.events.views import EventPublicInviteJoinAPIView
from apps.events.views import EventPublicInviteLinkAPIView
from apps.events.views import MyEventRSVPAPIView
from apps.events.views import UserEventAnalyticsAPIView

app_name = 'events'


urlpatterns = [
    # Event CRUD operations
    path('', EventListAPIView.as_view(), name='event-list'),  # GET/POST /events/
    path('<uuid:event_uuid>/', EventAPIView.as_view(), name='event-detail'),  # GET/PUT/DELETE /events/{uuid}/
    path(
        '<uuid:event_uuid>/participants/',
        EventParticipantListAPIView.as_view(),
        name='event-participants',
    ),
    path(
        '<uuid:event_uuid>/participants/<int:participant_id>/',
        EventParticipantAPIView.as_view(),
        name='event-participant-detail',
    ),
    path(
        '<uuid:event_uuid>/invites/public-link/',
        EventPublicInviteLinkAPIView.as_view(),
        name='event-public-invite-link',
    ),
    path(
        'invites/public-link/join/',
        EventPublicInviteJoinAPIView.as_view(),
        name='event-public-invite-join',
    ),
    # User's Own RSVP
    path('<uuid:event_uuid>/rsvp/', MyEventRSVPAPIView.as_view(), name='my-event-rsvp'),  # GET, PATCH
    # Analytics
    path(
        '<uuid:event_uuid>/analytics/',
        EventAnalyticsAPIView.as_view(),
        name='event-analytics',
    ),  # GET
    path(
        'analytics/user/',
        UserEventAnalyticsAPIView.as_view(),
        name='user-event-analytics',
    ),  # GET
]
