# Generated manually to populate user_uuid for existing users

import uuid

from django.db import migrations


def populate_user_uuids(apps, schema_editor):
    """Populate unique UUIDs for existing users"""
    User = apps.get_model('accounts', 'User')
    db_alias = schema_editor.connection.alias

    users_without_uuid = User.objects.using(db_alias).filter(user_uuid__isnull=True)
    for user in users_without_uuid:
        user.user_uuid = uuid.uuid4()
        user.save(update_fields=['user_uuid'])

    print(f'Populated UUID for {users_without_uuid.count()} users')


def reverse_populate_user_uuids(apps, schema_editor):
    """Reverse operation - clear UUIDs"""
    User = apps.get_model('accounts', 'User')
    db_alias = schema_editor.connection.alias
    User.objects.using(db_alias).update(user_uuid=None)


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0010_add_user_uuid_field'),
    ]

    operations = [
        migrations.RunPython(
            populate_user_uuids,
            reverse_populate_user_uuids,
        ),
    ]
