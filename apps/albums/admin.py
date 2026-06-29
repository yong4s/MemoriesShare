from django.contrib import admin

from apps.albums.models import Album


@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    list_select_related = ('event',)
    list_display = ('name', 'event', 'is_public', 'created_at')
    search_fields = ('name', 'event__event_name')
    list_filter = ('is_public',)
