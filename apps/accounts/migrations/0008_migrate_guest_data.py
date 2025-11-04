# Generated manually - Data migration to copy Guest data from events app

from django.db import migrations


def migrate_guest_data_forwards(apps, schema_editor):
    """Copy all guest data from events_guest table to accounts_guest table"""
    db_alias = schema_editor.connection.alias

    # Get the old and new Guest models
    EventsGuest = apps.get_model('events', 'Guest')
    AccountsGuest = apps.get_model('accounts', 'Guest')

    # Copy all guest records
    guests_to_create = []
    for old_guest in EventsGuest.objects.using(db_alias).all():
        guests_to_create.append(
            AccountsGuest(
                id=old_guest.id,
                created_at=old_guest.created_at,
                updated_at=old_guest.updated_at,
                name=old_guest.name,
                email=old_guest.email,
                phone_number=old_guest.phone_number,
                dietary_preferences=old_guest.dietary_preferences,
                rsvp_status=old_guest.rsvp_status,
                invitation_sent_at=old_guest.invitation_sent_at,
                responded_at=old_guest.responded_at,
                event_id=old_guest.event_id,
                user_id=old_guest.user_id,
            )
        )

    if guests_to_create:
        AccountsGuest.objects.using(db_alias).bulk_create(guests_to_create, batch_size=500)
        print(f'Migrated {len(guests_to_create)} guest records to accounts app')


def migrate_guest_data_backwards(apps, schema_editor):
    """Copy guest data back from accounts_guest to events_guest table"""
    db_alias = schema_editor.connection.alias

    # Get the old and new Guest models
    EventsGuest = apps.get_model('events', 'Guest')
    AccountsGuest = apps.get_model('accounts', 'Guest')

    # Copy all guest records back
    guests_to_create = []
    for new_guest in AccountsGuest.objects.using(db_alias).all():
        guests_to_create.append(
            EventsGuest(
                id=new_guest.id,
                created_at=new_guest.created_at,
                updated_at=new_guest.updated_at,
                name=new_guest.name,
                email=new_guest.email,
                phone_number=new_guest.phone_number,
                dietary_preferences=new_guest.dietary_preferences,
                rsvp_status=new_guest.rsvp_status,
                invitation_sent_at=new_guest.invitation_sent_at,
                responded_at=new_guest.responded_at,
                event_id=new_guest.event_id,
                user_id=new_guest.user_id,
            )
        )

    if guests_to_create:
        EventsGuest.objects.using(db_alias).bulk_create(guests_to_create, batch_size=500)
        print(f'Migrated {len(guests_to_create)} guest records back to events app')


class Migration(migrations.Migration):
    atomic = False  # Allow custom transaction handling

    dependencies = [
        ('accounts', '0007_add_guest_model'),
        ('events', '0014_alter_event_description'),
    ]

    operations = [
        migrations.RunPython(
            migrate_guest_data_forwards,
            migrate_guest_data_backwards,
        ),
    ]
