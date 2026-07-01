from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_customuser_preferred_login_method'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='password_changed_at',
            field=models.DateTimeField(
                blank=True,
                help_text='Timestamp of the last successful password set or change',
                null=True,
                verbose_name='Password Changed At',
            ),
        ),
    ]
