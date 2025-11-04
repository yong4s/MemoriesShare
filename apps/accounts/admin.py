from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    """Custom User Admin with Clerk integration support"""

    # Поля для відображення в списку користувачів
    list_display = ('pk', 'email', 'clerk_id', 'is_active', 'is_staff', 'date_joined', 'has_clerk_auth')
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'date_joined')
    search_fields = ('email', 'clerk_id', 'pk')
    ordering = ('-date_joined',)

    # Поля для детального перегляду користувача
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Clerk Integration'), {'fields': ('clerk_id',)}),
        (
            _('Permissions'),
            {
                'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            },
        ),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

    # Поля для створення нового користувача
    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': ('email', 'password1', 'password2', 'clerk_id'),
            },
        ),
    )

    # Readonly поля
    readonly_fields = ('date_joined', 'last_login')

    def has_clerk_auth(self, obj):
        """Показує чи має користувач Clerk аутентифікацію"""
        return bool(obj.clerk_id)

    has_clerk_auth.boolean = True
    has_clerk_auth.short_description = 'Clerk Auth'

    def get_queryset(self, request):
        """Оптимізований queryset"""
        return super().get_queryset(request).select_related()
