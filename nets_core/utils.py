import calendar
import logging
import os
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

logger = logging.getLogger(__name__)


def local_datetime(s: str, tz: str = settings.TIME_ZONE) -> datetime:
    """
    Parse an ISO-8601 datetime string and attach a timezone.

    Parameters
    ----------
    s:
        Naive ISO-8601 string, e.g. ``"2026-05-04T10:30:00"``.
    tz:
        IANA timezone name.  Defaults to ``settings.TIME_ZONE``.

    Returns
    -------
    datetime
        Timezone-aware datetime.

    Raises
    ------
    ValueError
        If *s* cannot be parsed as a datetime.
    """
    naive = parse_datetime(s)
    if not naive:
        raise ValueError("local_datetime: Not a valid datetime")

    return pytz.timezone(tz).localize(naive, is_dst=None)


def get_client_ip(request):
    """
    Extract the originating client IP address from *request*.

    Inspects a prioritised list of HTTP headers (``X-Forwarded-For``,
    ``X-Real-IP``, etc.) before falling back to ``REMOTE_ADDR``.  When
    multiple IPs are present in a comma-separated header (proxy chain), the
    **first** (leftmost) value is returned as per RFC 7239 convention.

    .. note::
        Only trust forwarded headers if your infrastructure guarantees they
        are set by a trusted reverse proxy.  In other deployments, consider
        using only ``REMOTE_ADDR``.
    """
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
    """
    Build a structured media upload path for a model ``FileField`` or
    ``ImageField``.

    The resulting path follows the pattern::

        <model_name>/<YYYY>/<MM>/<DD>/<filename>

    When the instance has a ``project`` attribute, the path is further
    namespaced::

        PSMDOC_PROJ_<project_id>/<model_name>/<YYYY>/<MM>/<DD>/<filename>

    This keeps uploaded files automatically organised by model and date,
    without any extra configuration per field.

    Example usage in a model
    ------------------------
    .. code-block:: python

        from nets_core.utils import get_upload_path

        class Invoice(OwnedModel):
            attachment = models.FileField(upload_to=get_upload_path)

    Parameters
    ----------
    instance:
        The model instance the file is being attached to.
    filename:
        Original filename supplied by the client.  The basename is extracted
        to prevent path-traversal attacks.

    Returns
    -------
    str
        Relative upload path.
    """
    # Strip any leading path components to prevent path-traversal.
    filename = os.path.basename(filename)
    folder = instance._meta.model_name
    path = ""
    if instance and hasattr(instance, "project"):
        path = f"PSMDOC_PROJ_{instance.project.id}/"

    path += "{}" .format(folder) if folder.endswith("/") else "{}/".format(folder)

    today = timezone.now()
    date_path = today.strftime("%Y/%m/%d/")
    path = "{}{}".format(path, date_path)
    path = "{}{}".format(path, filename)
    return path


def check_perm(user, action, project=None):
    """
    Check whether *user* holds a named permission, optionally within a project.

    Global permissions
    ------------------
    When *project* is ``None``, the function inspects all enabled
    :class:`~nets_core.models.UserRole` records for *user* and returns
    ``True`` if any attached :class:`~nets_core.models.Permission` matches
    *action*.

    Project-scoped permissions
    --------------------------
    When *project* is provided:

    1. Resolves the membership record from
       ``settings.NETS_CORE_PROJECT_MEMBER_MODEL``.
    2. Returns ``False`` if the member is disabled.
    3. Returns ``True`` immediately for project super-users.
    4. If *action* starts with ``"role:"`` (e.g. ``"role:admin"``), compares
       the member's ``role`` attribute directly.
    5. Otherwise, evaluates the user's project-scoped roles against
       :class:`~nets_core.models.RolePermission` records.

    Parameters
    ----------
    user:
        Instance of ``settings.AUTH_USER_MODEL``.
    action:
        Permission codename, e.g. ``"can_publish"``, or a role shorthand
        like ``"role:admin"``.
    project:
        Optional project instance.  Must match
        ``settings.NETS_CORE_PROJECT_MODEL``.

    Returns
    -------
    bool
    """
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
        except Exception:
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
        logger.debug("check_perm user=%s roles=%s perms=%s", user, list(user_roles), list(user_perms))
        for p in user_perms:
            logger.debug("check_perm evaluating codename=%s", p.codename)
            if p.codename == action:
                return True

        return False


