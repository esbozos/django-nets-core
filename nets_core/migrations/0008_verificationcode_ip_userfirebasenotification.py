# Generated by Django 4.1.7 on 2023-08-16 19:54

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('nets_core', '0007_alter_verificationcode_device'),
    ]

    operations = [
        migrations.AddField(
            model_name='verificationcode',
            name='ip',
            field=models.CharField(blank=True, max_length=150, null=True, verbose_name='IP'),
        ),
        migrations.CreateModel(
            name='UserFirebaseNotification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Created')),
                ('updated', models.DateTimeField(auto_now=True, verbose_name='updated')),
                ('message', models.TextField(blank=True, null=True, verbose_name='Message')),
                ('data', models.JSONField(blank=True, null=True, verbose_name='Data')),
                ('sent', models.BooleanField(default=False, verbose_name='Sent')),
                ('message_id', models.CharField(blank=True, max_length=250, null=True, verbose_name='Message ID')),
                ('error', models.TextField(blank=True, null=True, verbose_name='Error')),
                ('device', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='nets_core.userdevice')),
                ('devices', models.ManyToManyField(related_name='notifications', to='nets_core.userdevice')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'User Firebase Notification',
                'verbose_name_plural': 'User Firebase Notifications',
                'db_table': 'nets_core_firebase_notification',
            },
        ),
    ]
