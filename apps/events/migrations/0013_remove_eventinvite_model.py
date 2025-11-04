# Generated migration to remove EventInvite from events app

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('events', '0012_add_user_field_to_guest'),
        ('accounts', '0005_add_eventinvite_model'),
    ]

    operations = [
        # Since EventInvite was moved to accounts app, we don't need to remove indexes
        # The model never existed in the events app in the database
        # This migration is just for dependency tracking
    ]
