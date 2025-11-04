# Generated manually to fix duplicate user_uuid values

import uuid

from django.db import migrations


def fix_duplicate_uuids(apps, schema_editor):
    """Fix duplicate user_uuid values by generating new unique UUIDs"""
    User = apps.get_model('accounts', 'User')
    db_alias = schema_editor.connection.alias

    # Генеруємо нові унікальні UUID для всіх користувачів
    users = User.objects.using(db_alias).all()
    updated_count = 0

    for user in users:
        new_uuid = uuid.uuid4()
        # Перевіряємо що UUID унікальний
        while User.objects.using(db_alias).filter(user_uuid=new_uuid).exists():
            new_uuid = uuid.uuid4()

        user.user_uuid = new_uuid
        user.save(update_fields=['user_uuid'])
        updated_count += 1

    print(f'Updated {updated_count} users with unique UUIDs')


def reverse_fix_duplicate_uuids(apps, schema_editor):
    """Reverse operation - not implemented"""


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0011_populate_user_uuid'),
    ]

    operations = [
        migrations.RunPython(
            fix_duplicate_uuids,
            reverse_fix_duplicate_uuids,
        ),
    ]
