from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    """Custom User Admin for unified user types"""

    # Display fields in user list
    list_display = (
        "pk",
        "email",
        "user_type",
        "display_name",
        "is_active",
        "is_staff",
        "date_joined",
    )
    list_filter = (
        "is_registered",
        "is_active",
        "is_staff",
        "is_superuser",
        "date_joined",
    )
    search_fields = ("email", "guest_name", "first_name", "last_name", "pk")
    ordering = ("-date_joined",)

    # Fields for user detail view
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("User Type"), {"fields": ("is_registered", "guest_name")}),
        (_("Personal Info"), {"fields": ("first_name", "last_name", "user_uuid")}),
        (_("Guest Info"), {"fields": ("invite_token_used", "original_guest_data")}),
        (
            _("Event Participation"),
            {"fields": ("event_participation_summary",), "classes": ("collapse",)},
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (
            _("Important dates"),
            {"fields": ("last_login", "date_joined", "created_at", "updated_at")},
        ),
    )

    # Fields for creating new user
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "is_registered",
                    "first_name",
                    "last_name",
                    "guest_name",
                ),
            },
        ),
    )

    # Readonly fields
    readonly_fields = (
        "date_joined",
        "last_login",
        "created_at",
        "updated_at",
        "user_uuid",
        "event_participation_summary",
    )

    def user_type(self, obj):
        """Display user type based on is_registered flag"""
        if obj.is_registered:
            return "🔐 Registered"
        elif obj.email:
            return "📧 Passwordless"
        else:
            return "👤 Guest"

    user_type.short_description = "Type"

    def event_participation_summary(self, obj):
        """Summary of user's event participation"""
        from django.urls import reverse

        try:
            participations = obj.event_participations.select_related("event")
            if not participations.exists():
                return format_html(
                    '<span style="color: gray;">Не бере участь у подіях</span>'
                )

            total = participations.count()
            owner_count = participations.filter(role="OWNER").count()
            moderator_count = participations.filter(role="MODERATOR").count()
            guest_count = participations.filter(role="GUEST").count()

            # RSVP statistics
            accepted = participations.filter(rsvp_status="accepted").count()
            declined = participations.filter(rsvp_status="declined").count()
            pending = participations.filter(rsvp_status="pending").count()

            summary = [f"📊 <strong>Всього подій: {total}</strong>"]

            # Role breakdown
            roles = []
            if owner_count:
                roles.append(f"👑 Власник: {owner_count}")
            if moderator_count:
                roles.append(f"🛡️ Модератор: {moderator_count}")
            if guest_count:
                roles.append(f"👤 Гість: {guest_count}")
            if roles:
                summary.append("<br>".join(roles))

            # RSVP breakdown
            rsvp_info = []
            if accepted:
                rsvp_info.append(
                    f'<span style="color: green;">✅ Підтвердив: {accepted}</span>'
                )
            if declined:
                rsvp_info.append(
                    f'<span style="color: red;">❌ Відхилив: {declined}</span>'
                )
            if pending:
                rsvp_info.append(
                    f'<span style="color: orange;">⏳ Очікується: {pending}</span>'
                )
            if rsvp_info:
                summary.append("<br>" + " | ".join(rsvp_info))

            # Recent events
            recent_events = participations.order_by("-created_at")[:3]
            if recent_events:
                events_info = []
                for participation in recent_events:
                    event = participation.event
                    url = reverse("admin:events_event_change", args=[event.pk])
                    role_icon = (
                        "👑"
                        if participation.role == "OWNER"
                        else ("🛡️" if participation.role == "MODERATOR" else "👤")
                    )
                    events_info.append(
                        f'<a href="{url}">{role_icon} {event.event_name}</a>'
                    )
                summary.append(
                    "<br><strong>Останні події:</strong><br>" + "<br>".join(events_info)
                )

            return format_html("<br>".join(summary))

        except Exception as e:
            return format_html('<span style="color: red;">⚠️ Помилка: {}</span>', str(e))

    event_participation_summary.short_description = "Участь у подіях"

    def get_queryset(self, request):
        """Optimized queryset"""
        return (
            super()
            .get_queryset(request)
            .select_related()
            .prefetch_related("event_participations__event")
        )
