# Generated by Django 5.0.7 on 2024-07-26 19:23

import django.db.models.deletion
from django.db import migrations, models


def pre_migration(apps, schema_editor):
    Role = apps.get_model("nets_core", "Role")
    Permission = apps.get_model("nets_core", "Permission")

    ContentType = apps.get_model("contenttypes", "ContentType")
    unique_codenames = []
    for p in Permission.objects.all():
        if p.codename not in unique_codenames:
            unique_codenames.append(p.codename)
            other_permissions = Permission.objects.filter(codename=p.codename).exclude(
                id=p.id
            )
            if other_permissions.count() == 0:
                # update role permissions with the new permission
                for op in other_permissions:
                    for r in op.roles.all():
                        r.permissions.add(p)
                        r.permissions.remove(op)
                        r.save()
                # delete other permissions
                other_permissions.delete()
        else:
            p.delete()


def migrate_through(apps, schema_editor):
    Role = apps.get_model("nets_core", "Role")
    Permission = apps.get_model("nets_core", "Permission")
    RolePermission = apps.get_model("nets_core", "RolePermission")

    for role in Role.objects.all():
        for permission in role.permissions.all():
            RolePermission.objects.create(role=role, permission=permission)


class Migration(migrations.Migration):

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("nets_core", "0013_customemail_updated_fields_and_more"),
        
    ]

    operations = [
        migrations.RunPython(pre_migration),
        migrations.CreateModel(
            name="RolePermission",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created"),
                ),
                (
                    "updated",
                    models.DateTimeField(auto_now=True, verbose_name="updated"),
                ),
                (
                    "updated_fields",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        null=True,
                        verbose_name="Updated fields",
                    ),
                ),
                (
                    "custom_name",
                    models.CharField(
                        blank=True,
                        max_length=150,
                        null=True,
                        verbose_name="Custom name",
                    ),
                ),
            ],
            options={
                "verbose_name": "Role Permission",
                "verbose_name_plural": "Role Permissions",
                "db_table": "nets_core_role_permission",
            },
        ),
        migrations.AddField(
            model_name="rolepermission",
            name="role",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="nets_core.role"
            ),
        ),
        migrations.AddField(
            model_name="rolepermission",
            name="permission",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="nets_core.permission",
            ),
        ),                
        migrations.RunPython(migrate_through),
    ]
