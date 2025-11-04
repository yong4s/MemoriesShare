from django.contrib import admin

from apps.mediafiles.models import Download
from apps.mediafiles.models import MediaFile

admin.site.register(MediaFile)
admin.site.register(Download)
