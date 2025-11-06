from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    """Custom User Admin for unified user types"""

    # Display fields in user list
    list_display = ('pk', 'email', 'user_type', 'display_name', 'is_active', 'is_staff', 'date_joined')
    list_filter = ('is_registered', 'is_active', 'is_staff', 'is_superuser', 'date_joined')
    search_fields = ('email', 'guest_name', 'first_name', 'last_name', 'pk')
    ordering = ('-date_joined',)

    # Fields for user detail view
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('User Type'), {'fields': ('is_registered', 'guest_name')}),
        (_('Personal Info'), {'fields': ('first_name', 'last_name', 'user_uuid')}),
        (_('Guest Info'), {'fields': ('invite_token_used', 'original_guest_data')}),
        (
            _('Permissions'),
            {
                'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            },
        ),
        (_('Important dates'), {'fields': ('last_login', 'date_joined', 'created_at', 'updated_at')}),
    )

    # Fields for creating new user
    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': ('email', 'password1', 'password2', 'is_registered', 'first_name', 'last_name', 'guest_name'),
            },
        ),
    )

    # Readonly fields
    readonly_fields = ('date_joined', 'last_login', 'created_at', 'updated_at', 'user_uuid')

    def user_type(self, obj):
        """Display user type based on is_registered flag"""
        if obj.is_registered:
            return '🔐 Registered'
        elif obj.email:
            return '📧 Passwordless'
        else:
            return '👤 Guest'

    user_type.short_description = 'Type'

    def get_queryset(self, request):
        """Optimized queryset"""
        return super().get_queryset(request).select_related()
