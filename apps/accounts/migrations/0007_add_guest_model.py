# Generated manually for Guest model migration from events app

import django.db.models.deletion
from django.db import migrations
from django.db import models
from django.utils import timezone


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0006_rename_accounts_ev_event_i_a88cce_idx_accounts_ev_event_i_b24bd8_idx_and_more'),
        ('events', '0014_alter_event_description'),
    ]

    operations = [
        # Create the Guest model in accounts app
        migrations.CreateModel(
            name='Guest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Створено')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Оновлено')),
                ('name', models.CharField(db_index=True, help_text="Ім'я гостя", max_length=255, verbose_name="Ім'я")),
                (
                    'email',
                    models.EmailField(
                        db_index=True, help_text='Електронна пошта гостя', max_length=254, verbose_name='Email'
                    ),
                ),
                (
                    'phone_number',
                    models.CharField(
                        blank=True,
                        help_text='Номер телефону у форматі +XXXXXXXXXX',
                        max_length=15,
                        verbose_name='Номер телефону',
                    ),
                ),
                (
                    'dietary_preferences',
                    models.TextField(
                        blank=True,
                        help_text='Особливі дієтичні переваги або обмеження',
                        verbose_name='Дієтичні переваги',
                    ),
                ),
                (
                    'rsvp_status',
                    models.CharField(
                        choices=[
                            ('accepted', 'Підтверджено'),
                            ('declined', 'Відмовлено'),
                            ('pending', 'Очікується'),
                            ('tentative', 'Можливо'),
                            ('canceled', 'Скасовано'),
                            ('no_show', "Не з'явився"),
                            ('waitlisted', 'У списку очікування'),
                            ('maybe', 'Можливо'),
                            ('confirmed_plus_one', 'Підтверджено +1'),
                            ('declined_with_regret', 'Відмовлено з жалем'),
                        ],
                        db_index=True,
                        default='pending',
                        help_text='Статус відповіді на запрошення',
                        max_length=20,
                        verbose_name='Статус RSVP',
                    ),
                ),
                (
                    'invitation_sent_at',
                    models.DateTimeField(
                        blank=True,
                        help_text='Дата та час відправки запрошення',
                        null=True,
                        verbose_name='Запрошення відправлено',
                    ),
                ),
                (
                    'responded_at',
                    models.DateTimeField(
                        blank=True,
                        help_text='Дата та час отримання відповіді від гостя',
                        null=True,
                        verbose_name='Дата відповіді',
                    ),
                ),
                (
                    'event',
                    models.ForeignKey(
                        db_index=True,
                        help_text='Подія, до якої належить гість',
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='guests',
                        to='events.event',
                        verbose_name='Подія',
                    ),
                ),
                (
                    'user',
                    models.ForeignKey(
                        blank=True,
                        db_index=True,
                        help_text='Користувач-гість (якщо зареєстрований)',
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='guest_invitations',
                        to='accounts.user',
                        verbose_name='Користувач',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Гість',
                'verbose_name_plural': 'Гості',
                'ordering': ['name'],
                'indexes': [
                    models.Index(fields=['event', 'rsvp_status'], name='accounts_gu_event_i_c5b51b_idx'),
                    models.Index(fields=['event', 'email'], name='accounts_gu_event_i_3d1ff1_idx'),
                ],
            },
        ),
        migrations.AlterUniqueTogether(
            name='guest',
            unique_together={('event', 'email')},
        ),
    ]
