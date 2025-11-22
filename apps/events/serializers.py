"""
Clean Event Serializers for Unified Architecture

Simple, focused serializers that work with the "dumb" Event model
and clean service layer architecture.
"""

from django.utils import timezone
from rest_framework import serializers

from apps.events.models.event import Event
from apps.events.models.event_participant import EventParticipant

# =============================================================================
# EVENT SERIALIZERS
# =============================================================================


class EventCreateSerializer(serializers.ModelSerializer):
    """Create new event"""

    class Meta:
        model = Event
        fields = ['event_name', 'description', 'date', 'time', 'location', 'address', 'all_day', 'is_public']
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
            raise serializers.ValidationError('Event date cannot be in the past')
        return value


class EventDetailSerializer(serializers.ModelSerializer):
    """Event details with statistics"""

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
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Cache owner data to prevent N+1 queries
        self._owner_cache = {}
    
    def to_representation(self, instance):
        """Override to optimize owner data fetching"""
        # Pre-fetch owner data for all instances to prevent N+1
        if hasattr(self, 'parent') and self.parent and hasattr(self.parent, 'instance'):
            # This is part of a many=True serialization
            self._prefetch_owners_for_queryset()
        elif hasattr(instance, '_prefetched_objects_cache'):
            # Single instance with prefetch
            self._cache_owner_for_instance(instance)
        
        return super().to_representation(instance)
    
    def _prefetch_owners_for_queryset(self):
        """Pre-fetch owner data for multiple instances to prevent N+1"""
        if hasattr(self, '_owners_prefetched'):
            return
            
        instances = self.parent.instance if hasattr(self.parent, 'instance') else []
        if not instances:
            return
            
        # Get all event IDs
        event_ids = [instance.id for instance in instances if hasattr(instance, 'id')]
        if not event_ids:
            return
            
        # Fetch all owners in one query
        from apps.events.models.event_participant import EventParticipant
        owners = EventParticipant.objects.filter(
            event_id__in=event_ids,
            role=EventParticipant.Role.OWNER
        ).select_related('user', 'event')
        
        # Cache owners by event_id
        for owner in owners:
            self._owner_cache[owner.event_id] = owner
            
        self._owners_prefetched = True
    
    def _cache_owner_for_instance(self, instance):
        """Cache owner for single instance"""
        if instance.id not in self._owner_cache:
            try:
                owner = instance.eventparticipant_set.filter(role=EventParticipant.Role.OWNER).select_related('user').first()
                self._owner_cache[instance.id] = owner
            except Exception:
                self._owner_cache[instance.id] = None

    def get_owner_name(self, obj):
        """Get owner name from cached EventParticipant"""
        owner = self._owner_cache.get(obj.id)
        if owner is None:
            # Fallback for single instance without prefetch
            try:
                owner = obj.eventparticipant_set.filter(role=EventParticipant.Role.OWNER).select_related('user').first()
                self._owner_cache[obj.id] = owner
            except Exception:
                return 'Unknown'
        
        return owner.user.display_name if owner and owner.user else 'No Owner'

    def get_owner_email(self, obj):
        """Get owner email from cached EventParticipant"""
        owner = self._owner_cache.get(obj.id)
        if owner is None:
            # Fallback for single instance without prefetch
            try:
                owner = obj.eventparticipant_set.filter(role=EventParticipant.Role.OWNER).select_related('user').first()
                self._owner_cache[obj.id] = owner
            except Exception:
                return ''
        
        return owner.user.email if owner and owner.user else ''


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
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Cache owner data to prevent N+1 queries
        self._owner_cache = {}
    
    def to_representation(self, instance):
        """Override to optimize owner data fetching"""
        if isinstance(self.instance, list) and not hasattr(self, '_owners_prefetched'):
            self._prefetch_owners_for_list()
        elif hasattr(instance, '_prefetched_objects_cache'):
            self._cache_owner_for_instance(instance)
        
        return super().to_representation(instance)
    
    def _prefetch_owners_for_list(self):
        """Pre-fetch owner data for list view to prevent N+1"""
        if hasattr(self, '_owners_prefetched'):
            return
            
        instances = self.instance if isinstance(self.instance, list) else []
        if not instances:
            return
            
        # Get all event IDs
        event_ids = [instance.id for instance in instances if hasattr(instance, 'id')]
        if not event_ids:
            return
            
        # Fetch all owners in one query
        from apps.events.models.event_participant import EventParticipant
        owners = EventParticipant.objects.filter(
            event_id__in=event_ids,
            role=EventParticipant.Role.OWNER
        ).select_related('user')
        
        # Cache owners by event_id
        for owner in owners:
            self._owner_cache[owner.event_id] = owner
            
        self._owners_prefetched = True
    
    def _cache_owner_for_instance(self, instance):
        """Cache owner for single instance"""
        if instance.id not in self._owner_cache:
            try:
                owner = instance.eventparticipant_set.filter(role=EventParticipant.Role.OWNER).select_related('user').first()
                self._owner_cache[instance.id] = owner
            except Exception:
                self._owner_cache[instance.id] = None

    def get_owner_name(self, obj):
        """Get owner name from cached EventParticipant"""
        owner = self._owner_cache.get(obj.id)
        if owner is None:
            # Fallback for single instance without prefetch
            try:
                owner = obj.eventparticipant_set.filter(role=EventParticipant.Role.OWNER).select_related('user').first()
                self._owner_cache[obj.id] = owner
            except Exception:
                return 'Unknown'
        
        return owner.user.display_name if owner and owner.user else 'No Owner'


class EventUpdateSerializer(serializers.ModelSerializer):
    """Update existing event"""

    class Meta:
        model = Event
        fields = ['event_name', 'description', 'date', 'time', 'location', 'address', 'all_day', 'is_public']

    def validate_date(self, value):
        """Validate event date"""
        if value < timezone.now().date():
            raise serializers.ValidationError('Event date cannot be in the past')
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
        """Get owner name from EventParticipant - optimized version"""
        try:
            # Use select_related for single query optimization
            owner = obj.eventparticipant_set.filter(role=EventParticipant.Role.OWNER).select_related('user').first()
            return owner.user.display_name if owner and owner.user else 'No Owner'
        except Exception:
            return 'Unknown'


# =============================================================================
# PARTICIPANT SERIALIZERS
# =============================================================================


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
        fields = ['role', 'rsvp_status', 'guest_name', 'user_name', 'is_registered_user', 'created_at']
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
    guest_email = serializers.EmailField(required=False, allow_blank=True)

    def validate_guest_name(self, value):
        """Validate guest name"""
        if len(value.strip()) < 2:
            raise serializers.ValidationError('Guest name must be at least 2 characters')
        return value.strip()


class BulkGuestInviteSerializer(serializers.Serializer):
    """Invite multiple guests to event"""

    guests = serializers.ListField(child=GuestInviteSerializer(), min_length=1, max_length=50)


# =============================================================================
# QUERY PARAMETER SERIALIZERS
# =============================================================================


class EventListQuerySerializer(serializers.Serializer):
    """Query parameters for event list"""

    page = serializers.IntegerField(default=1, min_value=1)
    page_size = serializers.IntegerField(default=20, min_value=1, max_value=100)
    search = serializers.CharField(required=False, max_length=255)
    owned_only = serializers.BooleanField(default=False)




class ParticipantListQuerySerializer(serializers.Serializer):
    """Query parameters for participant list"""

    role = serializers.ChoiceField(choices=EventParticipant.Role.choices, required=False)
    rsvp_status = serializers.ChoiceField(choices=EventParticipant.RsvpStatus.choices, required=False)
