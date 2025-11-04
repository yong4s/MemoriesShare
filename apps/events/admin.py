from django.contrib import admin
from django.utils.html import format_html

from apps.events.models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    """Кастомна админка для подій з усіма полями."""

    list_display = ['event_name', 'user', 'date', 'is_public', 'participant_count_display', 'created_at']

    list_filter = ['is_public', 'date', 'created_at', 'user']

    search_fields = ['event_name', 'description', 'user__email', 'event_uuid']

    readonly_fields = ['event_uuid', 'created_at', 'updated_at', 'participant_count_display']

    fieldsets = (
        ('Основна інформація', {'fields': ('event_name', 'description', 'user', 'date', 'is_public', 'max_guests')}),
        ('Системні поля', {'fields': ('event_uuid', 'created_at', 'updated_at'), 'classes': ('collapse',)}),
        ('Статистика', {'fields': ('participant_count_display',), 'classes': ('collapse',)}),
    )

    def participant_count_display(self, obj):
        """Shows participant count through service layer."""
        try:
            from apps.events.services.event_service import EventService

            event_service = EventService()
            participants = event_service.get_event_participants(
                event_uuid=str(obj.event_uuid), requesting_user_id=obj.user_id if obj.user_id else 1
            )
            count = len(participants)
        except Exception:
            count = 0

        return format_html('<span style="color: {};">{} participants</span>', 'green' if count > 0 else 'gray', count)

    participant_count_display.short_description = 'Participant Count'


# GuestAdmin has been moved to apps.accounts.admin
