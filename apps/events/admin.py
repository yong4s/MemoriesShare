from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db import models
from django.utils.html import format_html
from django.utils import timezone

from .models import Event, EventParticipant

User = get_user_model()


class EventParticipantInline(admin.TabularInline):
    model = EventParticipant
    extra = 1
    fields = [
        "user",
        "role",
        "rsvp_status",
        "guest_name",
        "guest_email",
        "guest_phone",
        "dietary_preferences",
        "join_method",
        "invitation_sent_at",
        "responded_at",
    ]
    readonly_fields = ["invitation_sent_at", "responded_at", "invite_token_used"]
    autocomplete_fields = ["user"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user", "event")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "user":
            kwargs["queryset"] = User.objects.filter(is_active=True).order_by("email")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    inlines = [EventParticipantInline]

    list_display = [
        "event_name",
        "owner_display",
        "date_display",
        "time_display",
        "location_display",
        "participant_stats_display",
        "is_public",
        "created_at",
    ]

    list_filter = [
        "is_public",
        "date",
        "all_day",
        "created_at",
        "participants__role",
        "participants__rsvp_status",
    ]

    search_fields = [
        "event_name",
        "description",
        "location",
        "address",
        "participants__user__email",
        "participants__guest_name",
        "participants__guest_email",
    ]

    readonly_fields = [
        "event_uuid",
        "created_at",
        "updated_at",
        "participant_stats_display",
        "owner_display",
        "rsvp_breakdown_display",
        "guest_info_summary",
    ]

    fieldsets = (
        ("Basic Information", {"fields": ("event_name", "description", "is_public")}),
        ("Date and Time", {"fields": ("date", "time", "all_day")}),
        (
            "Location",
            {"fields": ("location", "address"), "classes": ("collapse",)},
        ),
        ("Technical Data", {"fields": ("s3_prefix",), "classes": ("collapse",)}),
        (
            "System Fields",
            {
                "fields": ("event_uuid", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
        (
            "Statistics",
            {
                "fields": (
                    "participant_stats_display",
                    "owner_display",
                    "rsvp_breakdown_display",
                    "guest_info_summary",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    actions = [
        "export_participant_list",
        "mark_events_as_public",
        "mark_events_as_private",
        "duplicate_event",
    ]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("user")
            .prefetch_related("participants__user")
            .annotate(
                participant_count=models.Count("participants"),
            )
        )

    def save_model(self, request, obj, form, change):
        if not change and not hasattr(obj, "user"):
            obj.user = request.user
        super().save_model(request, obj, form, change)

    def date_display(self, obj):
        now = timezone.now().date()
        if obj.date > now:
            icon = "🔮"
            color = "green"
        elif obj.date == now:
            icon = "⚡"
            color = "orange"
        else:
            icon = "📅"
            color = "gray"

        return format_html(
            '<span style="color: {};">{} {}</span>',
            color,
            icon,
            obj.date.strftime("%Y-%m-%d"),
        )

    date_display.short_description = "Event Date"

    def time_display(self, obj):
        if obj.all_day:
            return format_html('<span style="color: blue;">🕛 All Day</span>')
        return format_html(
            '<span style="color: black;">🕐 {}</span>', obj.time.strftime("%H:%M")
        )

    time_display.short_description = "Time"

    def location_display(self, obj):
        if not obj.location:
            return format_html('<span style="color: gray;">📍 No Location</span>')

        location_text = (
            obj.location[:30] + "..." if len(obj.location) > 30 else obj.location
        )
        return format_html('<span>📍 {}</span>', location_text)

    location_display.short_description = "Location"

    def participant_stats_display(self, obj):
        try:
            total = obj.participant_count
            if total == 0:
                return format_html('<span style="color: gray;">👥 No Participants</span>')

            owners = obj.participants.filter(role="OWNER").count()
            moderators = obj.participants.filter(role="MODERATOR").count()
            guests = obj.participants.filter(role="GUEST").count()

            stats = []
            if owners > 0:
                stats.append(f"👑 {owners}")
            if moderators > 0:
                stats.append(f"⚡ {moderators}")
            if guests > 0:
                stats.append(f"👤 {guests}")

            color = "green" if total > 5 else "orange" if total > 1 else "gray"
            return format_html(
                '<span style="color: {};">👥 {} ({})</span>',
                color,
                total,
                ", ".join(stats),
            )
        except Exception as e:
            return format_html('<span style="color: red;">Error: {}</span>', str(e))

    participant_stats_display.short_description = "Participants"

    def rsvp_breakdown_display(self, obj):
        try:
            participants = obj.participants.all()
            if not participants:
                return format_html('<span style="color: gray;">No Participants</span>')

            accepted = sum(1 for p in participants if p.rsvp_status == "ACCEPTED")
            declined = sum(1 for p in participants if p.rsvp_status == "DECLINED")
            pending = sum(1 for p in participants if p.rsvp_status == "PENDING")

            breakdown = []
            if accepted > 0:
                breakdown.append(f'<span style="color: green;">✅ {accepted}</span>')
            if declined > 0:
                breakdown.append(f'<span style="color: red;">❌ {declined}</span>')
            if pending > 0:
                breakdown.append(f'<span style="color: orange;">⏳ {pending}</span>')

            return format_html(" | ".join(breakdown))
        except Exception as e:
            return format_html('<span style="color: red;">Error: {}</span>', str(e))

    rsvp_breakdown_display.short_description = "RSVP Breakdown"

    def guest_info_summary(self, obj):
        try:
            guests = obj.participants.filter(role="GUEST")
            if not guests:
                return format_html('<span style="color: gray;">No Guests</span>')

            guests_with_dietary = guests.exclude(dietary_preferences="").count()
            guests_with_phone = guests.exclude(guest_phone="").count()

            info = [f"👤 {guests.count()}"]
            if guests_with_dietary > 0:
                info.append(f"🥗 Diet: {guests_with_dietary}")
            if guests_with_phone > 0:
                info.append(f"📞 Phone: {guests_with_phone}")

            return format_html(
                '<span style="color: blue;">{}</span>', " | ".join(info)
            )
        except Exception as e:
            return format_html('<span style="color: red;">Error: {}</span>', str(e))

    guest_info_summary.short_description = "Guest Information"

    def owner_display(self, obj):
        try:
            owner_participation = obj.participants.filter(role="OWNER").first()
            if owner_participation and owner_participation.user:
                user = owner_participation.user
                icon = (
                    "🔐"
                    if user.is_registered
                    else ("📧" if owner.user.email else "👤")
                )
                return format_html(
                    '<a href="/admin/auth/user/{}/change/">{} {}</a>',
                    user.id,
                    icon,
                    user.display_name,
                )
            return format_html('<span style="color: red;">❌ No Owner</span>')
        except Exception as e:
            return format_html('<span style="color: red;">⚠️ Error: {}</span>', str(e))

    owner_display.short_description = "Owner"

    def export_participant_list(self, request, queryset):
        count = 0
        for event in queryset:
            count += event.participants.count()

        self.message_user(
            request, f"Ready to export {count} participants from {queryset.count()} events."
        )

    export_participant_list.short_description = "Export Participant List"

    def mark_events_as_public(self, request, queryset):
        count = queryset.update(is_public=True)
        self.message_user(request, f"{count} events marked as public.")

    mark_events_as_public.short_description = "Mark as Public"

    def mark_events_as_private(self, request, queryset):
        count = queryset.update(is_public=False)
        self.message_user(request, f"{count} events marked as private.")

    mark_events_as_private.short_description = "Mark as Private"

    def duplicate_event(self, request, queryset):
        count = 0
        for event in queryset:
            event.pk = None
            event.event_uuid = None
            event.event_name = f"Copy - {event.event_name}"
            event.save()
            count += 1
        self.message_user(request, f"Created {count} event copies (without participants).")

    duplicate_event.short_description = "Duplicate Events"


class EventParticipantAdmin(admin.ModelAdmin):
    list_display = [
        "event_link",
        "participant_display",
        "role_display",
        "rsvp_status_display",
        "join_method",
        "contact_info",
        "invitation_sent_at",
        "responded_status",
    ]

    list_filter = [
        "role",
        "rsvp_status",
        "join_method",
        "invitation_sent_at",
        "responded_at",
        "event__is_public",
        ("dietary_preferences", admin.EmptyFieldListFilter),
        ("guest_phone", admin.EmptyFieldListFilter),
    ]

    search_fields = [
        "event__event_name",
        "user__email",
        "guest_name",
        "guest_email",
        "guest_phone",
        "dietary_preferences",
    ]

    readonly_fields = ["event_link", "invitation_sent_at", "responded_at"]

    fieldsets = (
        ("Basic Information", {"fields": ("event", "user", "role", "rsvp_status")}),
        (
            "Guest Information",
            {
                "fields": (
                    "guest_name",
                    "guest_email",
                    "guest_phone",
                    "dietary_preferences",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Invitation and Response",
            {
                "fields": (
                    "join_method",
                    "invite_token_used",
                    "invitation_sent_at",
                    "responded_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    actions = [
        "mark_as_accepted",
        "mark_as_declined",
        "mark_as_pending",
        "promote_to_moderator",
        "demote_to_guest",
        "send_invitation_reminder",
    ]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("event", "user")

    def event_link(self, obj):
        return format_html(
            '<a href="/admin/events/event/{}/change/">{}</a>',
            obj.event.id,
            obj.event.event_name,
        )

    event_link.short_description = "Event"

    def participant_display(self, obj):
        icon = (
            "🔐" if obj.user.is_registered else ("📧" if obj.user.email else "👤")
        )
        return format_html("{} {}", icon, obj.user.display_name)

    participant_display.short_description = "Participant"

    def role_display(self, obj):
        colors = {"OWNER": "red", "MODERATOR": "orange", "GUEST": "blue"}
        color = colors.get(obj.role, "black")
        return format_html('<span style="color: {};">{}</span>', color, obj.role)

    role_display.short_description = "Role"

    def rsvp_status_display(self, obj):
        colors = {"ACCEPTED": "green", "DECLINED": "red", "PENDING": "orange"}
        icons = {"ACCEPTED": "✅", "DECLINED": "❌", "PENDING": "⏳"}

        color = colors.get(obj.rsvp_status, "black")
        icon = icons.get(obj.rsvp_status, "❓")

        return format_html(
            '<span style="color: {};">{} {}</span>', color, icon, obj.rsvp_status
        )

    rsvp_status_display.short_description = "RSVP Status"

    def contact_info(self, obj):
        contact = []
        email = obj.contact_email
        phone = getattr(obj, "guest_phone", "")

        if email:
            contact.append(f"📧 {email}")
        if phone:
            contact.append(f"📞 {phone}")

        return format_html("<br>".join(contact)) if contact else "—"

    contact_info.short_description = "Contact"

    def responded_status(self, obj):
        if obj.responded_at:
            return format_html('<span style="color: green;">✅ Responded</span>')
        return format_html('<span style="color: orange;">⏳ Pending</span>')

    responded_status.short_description = "Response"

    def mark_as_accepted(self, request, queryset):
        count = queryset.update(rsvp_status="ACCEPTED")
        self.message_user(request, f"{count} participants marked as accepted.")

    mark_as_accepted.short_description = "Mark as Accepted"

    def mark_as_declined(self, request, queryset):
        count = queryset.update(rsvp_status="DECLINED")
        self.message_user(request, f"{count} participants marked as declined.")

    mark_as_declined.short_description = "Mark as Declined"

    def mark_as_pending(self, request, queryset):
        count = queryset.update(rsvp_status="PENDING")
        self.message_user(request, f"{count} participants marked as pending.")

    mark_as_pending.short_description = "Mark as Pending"

    def promote_to_moderator(self, request, queryset):
        count = queryset.exclude(role="OWNER").update(role="MODERATOR")
        self.message_user(request, f"{count} participants promoted to moderator.")

    promote_to_moderator.short_description = "Promote to Moderator"

    def demote_to_guest(self, request, queryset):
        count = queryset.exclude(role="OWNER").update(role="GUEST")
        self.message_user(request, f"{count} participants demoted to guest.")

    demote_to_guest.short_description = "Demote to Guest"

    def send_invitation_reminder(self, request, queryset):
        count = queryset.count()
        self.message_user(request, f"Invitation reminder sent to {count} participants.")

    send_invitation_reminder.short_description = "Send Reminder"


admin.site.register(EventParticipant, EventParticipantAdmin)