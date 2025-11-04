from django.urls import include
from django.urls import path

from .views import EventCreateAPIView
from .views import EventDeleteAPIView
from .views import EventDetailAPIView
from .views import EventListAPIView
from .views import EventUpdateAPIView

app_name = 'events'


urlpatterns = [
    # Event CRUD operations
    path('', EventListAPIView.as_view(), name='event-list'),  # GET /events/
    path('create/', EventCreateAPIView.as_view(), name='event-create'),  # POST /events/create/
    path('<uuid:event_uuid>/', EventDetailAPIView.as_view(), name='event-detail'),  # GET /events/{uuid}/
    path('update/', EventUpdateAPIView.as_view(), name='event-update'),  # PUT /events/update/ (event_uuid в payload)
    path('delete/', EventDeleteAPIView.as_view(), name='event-delete'),  # DELETE /events/delete/ (event_uuid в payload)
]
