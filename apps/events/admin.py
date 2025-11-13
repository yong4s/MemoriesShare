from django.contrib import admin
from django.utils.html import format_html

from apps.events.models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    """Кастомна админка для подій з усіма полями."""

    list_display = ['event_name', 'owner_display', 'date', 'is_public', 'participant_count_display', 'created_at']

    list_filter = ['is_public', 'date', 'created_at']

    search_fields = ['event_name', 'description', 'event_uuid']

    readonly_fields = ['event_uuid', 'created_at', 'updated_at', 'participant_count_display', 'owner_display']

    fieldsets = (
        ('Основна інформація', {'fields': ('event_name', 'description', 'date', 'is_public')}),
        ('Системні поля', {'fields': ('event_uuid', 'created_at', 'updated_at'), 'classes': ('collapse',)}),
        ('Статистика', {'fields': ('participant_count_display', 'owner_display'), 'classes': ('collapse',)}),
    )

    def participant_count_display(self, obj):
        """Shows participant count through service layer."""
        try:
            from apps.events.dal.event_participant_dal import EventParticipantDAL
            
            participant_dal = EventParticipantDAL()
            count = participant_dal.get_participants_count(obj)
        except Exception:
            count = 0

        return format_html('<span style="color: {};">{} participants</span>', 'green' if count > 0 else 'gray', count)

    participant_count_display.short_description = 'Participant Count'

    def owner_display(self, obj):
        """Shows event owner through EventParticipant."""
        try:
            from apps.events.dal.event_participant_dal import EventParticipantDAL
            
            participant_dal = EventParticipantDAL()
            owners = participant_dal.get_participants_by_role(obj, 'OWNER')
            if owners:
                owner = owners[0]
                return format_html('<span>{}</span>', owner.user.display_name)
            return format_html('<span style="color: red;">No Owner</span>')
        except Exception:
            return format_html('<span style="color: red;">Error</span>')

    owner_display.short_description = 'Owner'


# GuestAdmin has been moved to apps.accounts.admin
