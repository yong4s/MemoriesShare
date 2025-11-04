# Generated migration to move EventInvite from events to accounts app

import django.db.models.deletion
from django.conf import settings
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ('events', '0012_add_user_field_to_guest'),
        ('accounts', '0004_add_clerk_id_field'),
    ]

    operations = [
        migrations.CreateModel(
            name='EventInvite',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                (
                    'created_at',
                    models.DateTimeField(auto_now_add=True, help_text='Час створення запису', verbose_name='Створено'),
                ),
                (
                    'updated_at',
                    models.DateTimeField(
                        auto_now=True, help_text='Час останнього оновлення запису', verbose_name='Оновлено'
                    ),
                ),
                (
                    'guest_name',
                    models.CharField(
                        blank=True,
                        help_text="Ім'я запрошеного гостя (опціонально)",
                        max_length=255,
                        null=True,
                        verbose_name="Ім'я гостя",
                    ),
                ),
                (
                    'guest_email',
                    models.EmailField(
                        blank=True,
                        help_text='Email запрошеного гостя (опціонально)',
                        max_length=254,
                        null=True,
                        verbose_name='Email гостя',
                    ),
                ),
                (
                    'invite_token',
                    models.CharField(
                        db_index=True,
                        editable=False,
                        help_text='Унікальний токен для аутентифікації через QR-код',
                        max_length=64,
                        unique=True,
                        verbose_name='Токен запрошення',
                    ),
                ),
                (
                    'qr_code_data',
                    models.TextField(
                        blank=True,
                        help_text='URL або дані для генерації QR-коду',
                        null=True,
                        verbose_name='Дані QR-коду',
                    ),
                ),
                (
                    'is_active',
                    models.BooleanField(default=True, help_text='Чи активне запрошення', verbose_name='Активне'),
                ),
                (
                    'max_uses',
                    models.PositiveIntegerField(
                        default=1,
                        help_text='Скільки разів можна використати це запрошення (1 = одноразове)',
                        verbose_name='Максимальна кількість використань',
                    ),
                ),
                (
                    'used_count',
                    models.PositiveIntegerField(
                        default=0,
                        help_text='Скільки разів вже використовувалося це запрошення',
                        verbose_name='Кількість використань',
                    ),
                ),
                (
                    'expires_at',
                    models.DateTimeField(
                        blank=True,
                        help_text='Коли запрошення втрачає дійсність (залиште порожнім для безтермінового)',
                        null=True,
                        verbose_name='Термін дії',
                    ),
                ),
                (
                    'last_used_at',
                    models.DateTimeField(
                        blank=True,
                        help_text='Коли запрошення було використано останній раз',
                        null=True,
                        verbose_name='Останнє використання',
                    ),
                ),
                (
                    'event',
                    models.ForeignKey(
                        db_index=True,
                        help_text='Подія, для якої створено запрошення',
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='invites',
                        to='events.event',
                        verbose_name='Подія',
                    ),
                ),
                (
                    'guest_user',
                    models.ForeignKey(
                        blank=True,
                        help_text='Анонімний або зареєстрований користувач, що скористався запрошенням',
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='used_invites',
                        to=settings.AUTH_USER_MODEL,
                        verbose_name='Користувач-гість',
                    ),
                ),
                (
                    'invited_by',
                    models.ForeignKey(
                        db_index=True,
                        help_text='Користувач, який створив запрошення',
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='created_invites',
                        to=settings.AUTH_USER_MODEL,
                        verbose_name='Запросив',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Запрошення на подію',
                'verbose_name_plural': 'Запрошення на події',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='eventinvite',
            index=models.Index(fields=['event', 'is_active'], name='accounts_ev_event_i_a88cce_idx'),
        ),
        migrations.AddIndex(
            model_name='eventinvite',
            index=models.Index(fields=['invite_token'], name='accounts_ev_invite__fe3e92_idx'),
        ),
        migrations.AddIndex(
            model_name='eventinvite',
            index=models.Index(fields=['expires_at', 'is_active'], name='accounts_ev_expires_e7e4cb_idx'),
        ),
    ]
