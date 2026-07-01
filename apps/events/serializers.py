"""
Clean Event Serializers for Unified Architecture

Simple, focused serializers that work with the "dumb" Event model
and clean service layer architecture.
"""

from django.utils import timezone
from rest_framework import serializers

from apps.events.models.event import Event
from apps.events.models.event_participant import EventParticipant


class EventCreateSerializer(serializers.ModelSerializer):
    """Create new event"""

    class Meta:
        model = Event
        fields = [
            'event_name',
            'description',
            'date',
            'time',
            'location',
            'address',
            'all_day',
            'is_public',
        ]
        extra_kwargs = {
            'event_name': {'required': True, 'max_length': 255},
            'description': {'required': False, 'allow_blank': True},
            'date': {'required': True},
            'time': {'required': False, 'allow_null': True},
            'location': {'required': False, 'allow_blank': True},
            'address': {'required': False, 'allow_blank': True},
            'all_day': {'default': False},
            'is_public': {'default': False},
        }

    def validate_date(self, value):
        """Validate event date is not in the past"""
        if value < timezone.now().date():
            msg = 'Event date cannot be in the past'
            raise serializers.ValidationError(msg)
        return value


def _resolve_owner_participant(event):
    """Find OWNER participant via prefetched participants_through (0 queries when prefetch is active)."""
    for participation in event.participants_through.all():
        if participation.role == EventParticipant.Role.OWNER:
            return participation
    return None


class EventDetailSerializer(serializers.ModelSerializer):
    """Event details with statistics"""

    owner_id = serializers.SerializerMethodField()
    owner_name = serializers.SerializerMethodField()
    owner_email = serializers.SerializerMethodField()

    # Statistics from annotations (populated by EventQuerySet.with_statistics())
    total_participants = serializers.IntegerField(read_only=True)
    attending_count = serializers.IntegerField(read_only=True)
    not_attending_count = serializers.IntegerField(read_only=True)
    maybe_count = serializers.IntegerField(read_only=True)
    pending_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Event
        fields = [
            'event_uuid',
            'event_name',
            'description',
            'date',
            'time',
            'location',
            'address',
            'all_day',
            'is_public',
            'owner_id',
            'owner_name',
            'owner_email',
            'created_at',
            'updated_at',
            'total_participants',
            'attending_count',
            'not_attending_count',
            'maybe_count',
            'pending_count',
        ]
        read_only_fields = [
            'event_uuid',
            'owner_id',
            'owner_name',
            'owner_email',
            'created_at',
            'updated_at',
            'total_participants',
            'attending_count',
            'not_attending_count',
            'maybe_count',
            'pending_count',
        ]

    def get_owner_id(self, obj):
        owner = _resolve_owner_participant(obj)
        return owner.user_id if owner else None

    def get_owner_name(self, obj):
        owner = _resolve_owner_participant(obj)
        if owner and owner.user:
            return owner.user.display_name
        return 'No Owner'

    def get_owner_email(self, obj):
        owner = _resolve_owner_participant(obj)
        if owner and owner.user:
            return owner.user.email
        return ''


class EventListSerializer(serializers.ModelSerializer):
    """Event list item with basic info and statistics"""

    owner_name = serializers.SerializerMethodField()

    # Statistics from annotations
    total_participants = serializers.IntegerField(read_only=True)
    attending_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Event
        fields = [
            'event_uuid',
            'event_name',
            'date',
            'time',
            'location',
            'is_public',
            'owner_name',
            'created_at',
            'total_participants',
            'attending_count',
        ]
        read_only_fields = fields

    def get_owner_name(self, obj):
        owner = _resolve_owner_participant(obj)
        if owner and owner.user:
            return owner.user.display_name
        return 'No Owner'


class EventUpdateSerializer(serializers.ModelSerializer):
    """Update existing event"""

    class Meta:
        model = Event
        fields = [
            'event_name',
            'description',
            'date',
            'time',
            'location',
            'address',
            'all_day',
            'is_public',
        ]

    def validate_date(self, value):
        """Validate event date"""
        if value < timezone.now().date():
            msg = 'Event date cannot be in the past'
            raise serializers.ValidationError(msg)
        return value


class EventCreatedResponseSerializer(serializers.ModelSerializer):
    """Response after event creation"""

    owner_name = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            'event_uuid',
            'event_name',
            'description',
            'date',
            'time',
            'location',
            'is_public',
            'owner_name',
            'created_at',
        ]
        read_only_fields = fields

    def get_owner_name(self, obj):
        owner = _resolve_owner_participant(obj)
        if owner and owner.user:
            return owner.user.display_name
        return 'No Owner'


class EventParticipantDetailSerializer(serializers.ModelSerializer):
    """Detailed participant information"""

    user_name = serializers.CharField(source='user.display_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    is_registered_user = serializers.BooleanField(source='user.is_registered', read_only=True)

    class Meta:
        model = EventParticipant
        fields = [
            'role',
            'rsvp_status',
            'guest_name',
            'guest_email',
            'user_name',
            'user_email',
            'is_registered_user',
            'invite_token_used',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'user_name',
            'user_email',
            'is_registered_user',
            'invite_token_used',
            'created_at',
            'updated_at',
        ]


class EventParticipantListSerializer(serializers.ModelSerializer):
    """Participant list item"""

    user_name = serializers.CharField(source='user.display_name', read_only=True)
    is_registered_user = serializers.BooleanField(source='user.is_registered', read_only=True)

    class Meta:
        model = EventParticipant
        fields = [
            'role',
            'rsvp_status',
            'guest_name',
            'user_name',
            'is_registered_user',
            'created_at',
        ]
        read_only_fields = fields


class EventParticipantCreateSerializer(serializers.Serializer):
    """Add participant to event"""

    role = serializers.ChoiceField(choices=EventParticipant.Role.choices, default=EventParticipant.Role.GUEST)
    guest_name = serializers.CharField(required=False, allow_blank=True, max_length=255)
    guest_email = serializers.EmailField(required=False, allow_blank=True)


class EventParticipantRSVPUpdateSerializer(serializers.Serializer):
    """Update participant RSVP status"""

    rsvp_status = serializers.ChoiceField(choices=EventParticipant.RsvpStatus.choices, required=True)


class GuestInviteSerializer(serializers.Serializer):
    """Invite guest to event"""

    guest_name = serializers.CharField(max_length=255, min_length=2)
    guest_email = serializers.EmailField(required=True)

    def validate_guest_name(self, value):
        """Validate guest name"""
        if len(value.strip()) < 2:
            msg = 'Guest name must be at least 2 characters'
            raise serializers.ValidationError(msg)
        return value.strip()


class BulkGuestInviteSerializer(serializers.Serializer):
    """Invite multiple guests to event"""

    guests = serializers.ListField(child=GuestInviteSerializer(), min_length=1, max_length=50)


class EventPublicInviteIssueSerializer(serializers.Serializer):
    """Input for issuing a shared public invite URL."""

    ttl_hours = serializers.IntegerField(required=False, default=24, min_value=1, max_value=168)
    max_uses = serializers.IntegerField(required=False, default=10000, min_value=1, max_value=100000)


class EventPublicInviteIssueResponseSerializer(serializers.Serializer):
    """Response with URL for frontend-side QR generation."""

    invite_url = serializers.URLField()
    reused = serializers.BooleanField()
    max_uses = serializers.IntegerField()
    expires_at = serializers.CharField(allow_null=True)


class EventPublicInviteJoinSerializer(serializers.Serializer):
    """Input for joining an event via signed public invite link."""

    invite_token = serializers.CharField(max_length=1024)


class EventPublicInviteJoinResponseSerializer(serializers.Serializer):
    """Join result payload for signed public invite flow."""

    event_uuid = serializers.UUIDField()
    event_name = serializers.CharField()
    participant_id = serializers.IntegerField()
    participant_name = serializers.CharField()
    already_joined = serializers.BooleanField()


class EventListQuerySerializer(serializers.Serializer):
    """Query parameters for event list"""

    page = serializers.IntegerField(default=1, min_value=1)
    page_size = serializers.IntegerField(default=20, min_value=1, max_value=100)
    search = serializers.CharField(required=False, max_length=255)
    scope = serializers.ChoiceField(
        choices=['all', 'owned', 'participating', 'public'],
        default='all',
    )


class ParticipantListQuerySerializer(serializers.Serializer):
    """Query parameters for participant list"""

    role = serializers.ChoiceField(choices=EventParticipant.Role.choices, required=False)
    rsvp_status = serializers.ChoiceField(choices=EventParticipant.RsvpStatus.choices, required=False)
