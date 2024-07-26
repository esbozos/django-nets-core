import calendar
import time
import uuid
import re
from datetime import date, datetime

from django.contrib.contenttypes.models import ContentType
from django.apps import apps
from django.utils import timezone

import pytz
from django.conf import settings
from django.utils.dateparse import parse_datetime


def local_datetime(s: str, tz: str = settings.TIME_ZONE) -> datetime:
    naive = parse_datetime(s)
    if not naive:
        raise ValueError("local_datetime: Not a valid datetime")

    return pytz.timezone(tz).localize(naive, is_dst=None)


def get_client_ip(request):
    META_PRECEDENCE_ORDER = (
        "HTTP_X_FORWARDED_FOR",
        "X_FORWARDED_FOR",  # <client>, <proxy1>, <proxy2>
        "HTTP_CLIENT_IP",
        "HTTP_X_REAL_IP",
        "HTTP_X_FORWARDED",
        "HTTP_X_CLUSTER_CLIENT_IP",
        "HTTP_FORWARDED_FOR",
        "HTTP_FORWARDED",
        "HTTP_VIA",
        "REMOTE_ADDR",
    )

    for h in META_PRECEDENCE_ORDER:
        ip = request.META.get(h, None)
        if ip:
            if "," in ip:
                ip = ip.split(",")[0]
            return ip
    return None


def generate_int_uuid(size=None):
    u = uuid.uuid1()
    n_random = "{}".format(u.time_low)

    time_epoch = str(calendar.timegm(time.gmtime()))

    u_id = "{}{}".format(n_random, time_epoch)

    if size:
        u_id = u_id[:size]
    return int(u_id)


def get_upload_path(instance, filename):
    folder = instance._meta.model_name
    path = ""
    if instance and hasattr(instance, "project"):
        path = f"PSMDOC_PROJ_{instance.project.id}/"

    path += "{}".format(folder) if folder.endswith("/") else "{}/".format(folder)

    today = timezone.now()
    date_path = today.strftime("%Y/%m/%d/")
    path = "{}{}".format(path, date_path)
    path = "{}{}".format(path, filename)
    return path


def check_perm(user, action, project=None):
    from nets_core.models import Permission, RolePermission

    project_content_type = None
    project_id = None
    if user.is_superuser:
        return True

    if project:
        project_content_type = ContentType.objects.get_for_model(project)
        project_id = project.id

    if not Permission.objects.filter(codename=action).exists():
        # create permission and return False because this permission does not exist
        permission = Permission.objects.create(
            codename=action, name=action.replace("_", " ").capitalize()
        )
        return False

    if project:

        try:
            project_member_model = apps.get_model(
                settings.NETS_CORE_PROJECT_MEMBER_MODEL
            )
            try:
                member = project_member_model.objects.get(user=user, project=project)
                if hasattr(member, "enabled") and not member.enabled:
                    return False
                if hasattr(member, "is_superuser") and member.is_superuser:
                    return True
                
                if hasattr(member, 'role'):
                    if action.startswith('role:'):
                        return member.role.name.lower() == action.split(':')[1].lower()
                
            except project_member_model.DoesNotExist:
                return False
        except:
            raise Exception(
                "check_perm failed NETS_CORE_PROJECT_MEMBER_MODEL not set in settings"
            )

        user_roles = member.user.roles.filter(
            project_content_type=project_content_type, project_id=project_id
        )
        
        
        if user_roles.exists():            
            roles = [u.role for u in user_roles]
            return RolePermission.objects.filter(
                role__in=roles,
                permission__codename=action.lower(),
            ).exists()
        else:
            return False

    else:
        user_roles = user.roles.filter(role__enabled=True)
        user_perms = []
        for r in user_roles:
            user_perms += r.role.permissions.all()
        print(f"User: {user}", user_roles, user_perms)
        for p in user_perms:
            print(p.codename)
            if p.codename == action:
                return True

        return False
