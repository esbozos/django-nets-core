# Generated by Django 5.0.4 on 2024-05-20 15:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('nets_core', '0012_permission_created_permission_updated_role_created_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='customemail',
            name='updated_fields',
            field=models.JSONField(blank=True, default=dict, null=True, verbose_name='Updated fields'),
        ),
        migrations.AddField(
            model_name='emailnotification',
            name='updated_fields',
            field=models.JSONField(blank=True, default=dict, null=True, verbose_name='Updated fields'),
        ),
        migrations.AddField(
            model_name='emailtemplate',
            name='updated_fields',
            field=models.JSONField(blank=True, default=dict, null=True, verbose_name='Updated fields'),
        ),
        migrations.AddField(
            model_name='permission',
            name='updated_fields',
            field=models.JSONField(blank=True, default=dict, null=True, verbose_name='Updated fields'),
        ),
        migrations.AddField(
            model_name='role',
            name='updated_fields',
            field=models.JSONField(blank=True, default=dict, null=True, verbose_name='Updated fields'),
        ),
        migrations.AddField(
            model_name='userdevice',
            name='updated_fields',
            field=models.JSONField(blank=True, default=dict, null=True, verbose_name='Updated fields'),
        ),
        migrations.AddField(
            model_name='userfirebasenotification',
            name='updated_fields',
            field=models.JSONField(blank=True, default=dict, null=True, verbose_name='Updated fields'),
        ),
        migrations.AddField(
            model_name='userrole',
            name='updated_fields',
            field=models.JSONField(blank=True, default=dict, null=True, verbose_name='Updated fields'),
        ),
        migrations.AddField(
            model_name='verificationcode',
            name='updated_fields',
            field=models.JSONField(blank=True, default=dict, null=True, verbose_name='Updated fields'),
        ),
    ]
