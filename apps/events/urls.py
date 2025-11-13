from django.urls import include
from django.urls import path

from .views import EventCreateAPIView
from .views import EventDeleteAPIView
from .views import EventDetailAPIView
from .views import EventListAPIView
from .views import EventUpdateAPIView
from .views import MyEventsAPIView
from .views import EventParticipantListAPIView
from .views import EventParticipantDetailAPIView
from .views import EventParticipantRSVPUpdateAPIView
from .views import EventGuestInviteAPIView
from .views import EventBulkGuestInviteAPIView
from .views import MyEventRSVPAPIView
from .views import EventAnalyticsAPIView
from .views import UserEventAnalyticsAPIView

app_name = 'events'


urlpatterns = [
    # Event CRUD operations
    path('', EventListAPIView.as_view(), name='event-list'),  # GET /events/
    path('my/', MyEventsAPIView.as_view(), name='my-events'),  # GET /events/my/
    path('create/', EventCreateAPIView.as_view(), name='event-create'),  # POST /events/create/
    path('<uuid:event_uuid>/', EventDetailAPIView.as_view(), name='event-detail'),  # GET /events/{uuid}/
    path('<uuid:event_uuid>/update/', EventUpdateAPIView.as_view(), name='event-update'),  # PUT /events/{uuid}/update/
    path('<uuid:event_uuid>/delete/', EventDeleteAPIView.as_view(), name='event-delete'),  # DELETE /events/{uuid}/delete/
    
    # Event Participant Management
    path('<uuid:event_uuid>/participants/', EventParticipantListAPIView.as_view(), name='event-participants'),  # GET
    path('<uuid:event_uuid>/participants/<int:participant_id>/', EventParticipantDetailAPIView.as_view(), name='event-participant-detail'),  # GET
    path('<uuid:event_uuid>/participants/<int:participant_id>/rsvp/', EventParticipantRSVPUpdateAPIView.as_view(), name='event-participant-rsvp'),  # PATCH
    
    # Event Invitations
    path('<uuid:event_uuid>/invite/', EventGuestInviteAPIView.as_view(), name='event-invite-guest'),  # POST
    path('<uuid:event_uuid>/invite/bulk/', EventBulkGuestInviteAPIView.as_view(), name='event-invite-bulk'),  # POST
    
    # User's Own RSVP
    path('<uuid:event_uuid>/rsvp/', MyEventRSVPAPIView.as_view(), name='my-event-rsvp'),  # GET, PATCH
    
    # Analytics
    path('<uuid:event_uuid>/analytics/', EventAnalyticsAPIView.as_view(), name='event-analytics'),  # GET
    path('analytics/user/', UserEventAnalyticsAPIView.as_view(), name='user-event-analytics'),  # GET
]
