import hmac
import hashlib
import logging
from django.apps import apps
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from oauthlib import common
from oauth2_provider.models import Application, AccessToken, RefreshToken

logger = logging.getLogger(__name__)

# TODO: create middleware to restring token_access with device_uuid


def validate_verification_code(user, code: str) -> bool:
    """
    Validate a one-time verification code for *user* without consuming it.

    Delegates actual validation to ``VerificationCode.validate()``, which
    checks expiration and attempt limits.

    Parameters
    ----------
    user:
        Instance of ``settings.AUTH_USER_MODEL``.
    code:
        The raw OTP string entered by the user.

    Returns
    -------
    bool
        ``True`` if the code is valid and not expired; ``False`` otherwise.
    """
    try:
        from nets_core.models import VerificationCode
    except Exception as exc:
        raise Exception(_("nets_core.models not found")) from exc
    vcode = VerificationCode.objects.filter(user=user).last()
    if not vcode:
        return False
    return vcode.validate(code)


def authenticate(
    user, code: str, client_id: str, client_secret: str, device_uuid: str = None
) -> dict:
    """
    Check client_id and client_secret, validate verification code and
    create access and refresh tokens for oauth2
    raise Exception if any of this fail.

    Parameters:
    user (instance): Instance of settings.AUTH_MODEL_MODEL

    Returns:
    dict: {"access_token": str, "refresh_token": str, "token_expires": datetime }

    Raise:
    Exception: If client_id, client_secret or code are not valid.

    example of usage:
        try:
            tokens = authenticate(user, '123456', 'client_id_app', 'client_secret_app')
            # return tokens to your user here

        except Exception as e:
            msg = e.__str__()
            # your code if fail here
    """

    try:
        from nets_core.models import VerificationCode
    except Exception as exc:
        raise Exception(_("nets_core.models not found")) from exc

    try:
        oauth_app = Application.objects.get(client_id=client_id)
    except Application.DoesNotExist:
        raise Exception(_("Invalid client_id"))

    # Constant-time comparison to prevent timing-based secret enumeration.
    if not hmac.compare_digest(oauth_app.client_secret, client_secret):
        raise Exception(_("Invalid client_secret"))

    vcode = VerificationCode.objects.filter(user=user).order_by("-created").first()
    if not vcode:
        raise Exception(_("User has not requested verification code"))

    if not vcode.validate(code, device_uuid=device_uuid):
        raise Exception(_("Invalid code for this user and device"))

    if vcode.device:
        vcode.device.last_login = timezone.now()
        vcode.device.save()

    # update code as verified
    vcode.verified = True
    vcode.save()

    if hasattr(user, "email_verified") and not user.email_verified:
        user.email_verified = True
    user.last_login = timezone.now()
    user.save()

    # Create access and refresh token
    expires = get_expiration_time()
    
    return generate_tokens(user, oauth_app, expires)

def get_expiration_time():
    """
    Compute the OAuth2 access-token expiration datetime.

    Reads ``settings.ACCESS_TOKEN_EXPIRE_SECONDS`` when available;
    defaults to **30 days** (``60 * 60 * 24 * 30``).

    Returns
    -------
    datetime
        Timezone-aware expiration datetime.
    """
    expire_seconds = 60 * 60 * 24 * 30  # 30 days default
    expire_seconds = getattr(settings, "ACCESS_TOKEN_EXPIRE_SECONDS", expire_seconds)
    return timezone.now() + timezone.timedelta(seconds=expire_seconds)

def generate_tokens(user, oauth_app, expires=None):
    """
    Create a new OAuth2 ``AccessToken`` / ``RefreshToken`` pair for *user*.

    Parameters
    ----------
    user:
        Instance of ``settings.AUTH_USER_MODEL``.
    oauth_app:
        ``oauth2_provider.models.Application`` the tokens are issued for.
    expires:
        Optional timezone-aware expiration datetime.  When omitted,
        :func:`get_expiration_time` is used.

    Returns
    -------
    dict
        ``{"access_token": str, "refresh_token": str, "token_expire": datetime}``
    """
    if not expires:
        expires = get_expiration_time()
    
    access_token = AccessToken.objects.create(
        user=user,
        expires=expires,
        scope="",
        token=common.generate_token(),
        application=oauth_app,
    )

    refresh_token = RefreshToken.objects.create(
        user=user,
        token=common.generate_token(),
        application=oauth_app,
        access_token=access_token,
    )
    return {
        "access_token": access_token.token,
        "refresh_token": refresh_token.token,
        "token_expire": access_token.expires,
    }


def get_or_create_project_role(project, role_name):
    """
    Return (or create) a :class:`~nets_core.models.Role` scoped to *project*.

    Role names are automatically suffixed with ``_{project.id}`` to keep them
    unique across projects of the same type.

    Parameters
    ----------
    project:
        Instance of the model declared in ``settings.NETS_CORE_PROJECT_MODEL``.
    role_name:
        Human-readable role identifier, e.g. ``"admin"`` or ``"viewer"``.

    Returns
    -------
    tuple[Role, bool]
        The role instance and a boolean indicating whether it was created.

    Raises
    ------
    Exception
        If the project instance type does not match
        ``settings.NETS_CORE_PROJECT_MODEL`` or the model cannot be resolved.
    """
    try:
        from nets_core.models import Role
    except Exception as exc:
        raise Exception(_("nets_core.models not found")) from exc

    try:
        project_model = apps.get_model(settings.NETS_CORE_PROJECT_MODEL)
    except LookupError as exc:
        raise Exception(
            _("Could not resolve NETS_CORE_PROJECT_MODEL: %s") % settings.NETS_CORE_PROJECT_MODEL
        ) from exc

    if not isinstance(project, project_model):
        raise Exception(
            _("Invalid project instance. Should be the same as settings.NETS_CORE_PROJECT_MODEL")
        )

    content_type = ContentType.objects.get_for_model(project)
    if not role_name.endswith(f"_{project.id}"):
        role_name = f"{role_name}_{project.id}"
    role, _role_created = Role.objects.get_or_create(
        name=role_name, project_content_type=content_type, project_id=project.id
    )

    return role, _role_created


def get_or_create_project_role_permission(
    project, role_name, codename, verbose_name: str = None, description: str = ""
):
    """
    Ensure a :class:`~nets_core.models.Permission` exists and is attached to a
    project-scoped role.

    Creates the role (via :func:`get_or_create_project_role`) and the permission
    if they do not already exist, then links the permission to the role.

    Parameters
    ----------
    project:
        Instance of the model declared in ``settings.NETS_CORE_PROJECT_MODEL``.
    role_name:
        Role identifier (see :func:`get_or_create_project_role`).
    codename:
        Unique machine-readable permission string, e.g. ``"can_publish"``.
    verbose_name:
        Human-readable permission name.  Defaults to a titlecased version of
        *codename*.
    description:
        Optional longer description stored on the Permission record.

    Returns
    -------
    tuple[Permission, bool]
        The permission instance and a boolean indicating whether it was created.
    """
    try:
        from nets_core.models import Permission
    except Exception as exc:
        raise Exception(_("nets_core.models not found")) from exc
    role, _role_created = get_or_create_project_role(project, role_name)
    content_type = ContentType.objects.get_for_model(project)
    if not verbose_name:
        verbose_name = codename.replace("_", " ").capitalize()
    permission, _permission_created = Permission.objects.get_or_create(
        codename=codename, defaults={"name": verbose_name, "description": description}
    )

    role.permissions.add(permission)
    return permission, _permission_created


def add_user_to_role(user, project, role_name):
    """
    Assign *user* to a project-scoped role, creating the role if needed.

    Parameters
    ----------
    user:
        Instance of ``settings.AUTH_USER_MODEL``.
    project:
        Instance of the model declared in ``settings.NETS_CORE_PROJECT_MODEL``.
    role_name:
        Role identifier (see :func:`get_or_create_project_role`).

    Returns
    -------
    tuple[UserRole, bool]
        The ``UserRole`` join record and a boolean indicating whether it was
        created.

    Raises
    ------
    Exception
        If either model instance does not match the configured model types, or
        if the model labels cannot be resolved.
    """
    try:
        from nets_core.models import UserRole
    except Exception as exc:
        raise Exception(_("nets_core.models not found")) from exc

    try:
        project_model = apps.get_model(settings.NETS_CORE_PROJECT_MODEL)
    except LookupError as exc:
        raise Exception(
            _("Could not resolve NETS_CORE_PROJECT_MODEL: %s") % settings.NETS_CORE_PROJECT_MODEL
        ) from exc

    if not isinstance(project, project_model):
        raise Exception(
            _("Invalid project instance. Should be the same as settings.NETS_CORE_PROJECT_MODEL")
        )

    try:
        user_model = apps.get_model(settings.AUTH_USER_MODEL)
    except LookupError as exc:
        raise Exception(
            _("Could not resolve AUTH_USER_MODEL: %s") % settings.AUTH_USER_MODEL
        ) from exc

    if not isinstance(user, user_model):
        raise Exception(
            _("Invalid user instance. Should be the same as settings.AUTH_USER_MODEL")
        )

    role, _role_created = get_or_create_project_role(project, role_name)
    project_content_type = ContentType.objects.get_for_model(project)
    user_role, _user_role_created = UserRole.objects.get_or_create(
        user=user,
        role=role,
        project_content_type=project_content_type,
        project_id=project.id,
    )

    return user_role, _user_role_created


class SecureCache:
    """
    HMAC-backed cache wrapper for storing and validating short-lived secrets.

    Both keys and values are hashed with HMAC-SHA256 before they reach the
    cache backend.  This means:

    * The raw key is never stored — a compromised cache server cannot enumerate
      what logical keys exist.
    * The raw value is never stored — you cannot retrieve the original string,
      only verify it with :meth:`validate`.
    * Cache poisoning is mitigated: injecting an arbitrary value cannot pass
      validation without knowing ``SECRET_KEY`` (or
      ``NETS_CORE_SECURE_CACHE_KEY``).

    The HMAC secret is read from ``settings.NETS_CORE_SECURE_CACHE_KEY`` when
    present, falling back to Django's ``settings.SECRET_KEY``.

    Typical usage
    -------------
    .. code-block:: python

        sc = SecureCache()

        # Store a one-time token for 5 minutes:
        sc.set("password_reset:user_42", raw_token, expiration=300)

        # Later, verify the token submitted by the user:
        if sc.validate("password_reset:user_42", submitted_token):
            sc.delete("password_reset:user_42")
            # proceed with reset
    """

    def __init__(self):
        self.key = ""
        self.expiration = 0

    def secure_key(self, key: str) -> str:
        """Return the HMAC-SHA256 digest of *key*, prefixed and length-capped."""
        key_prefix = "NETS_SK_"
        secret_key = getattr(
            settings, "NETS_CORE_SECURE_CACHE_KEY", settings.SECRET_KEY
        )
        digest = hmac.new(
            secret_key.encode("utf-8"), key.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        k = f"{key_prefix}{digest}"
        if len(k) > 250:
            k = k[:250]
        return k

    def secure_value(self, value: str) -> str:
        """Return the HMAC-SHA256 digest of *value* (one-way; not reversible)."""
        secret_key = getattr(
            settings, "NETS_CORE_SECURE_CACHE_KEY", settings.SECRET_KEY
        )
        return hmac.new(
            secret_key.encode("utf-8"), value.encode("utf-8"), hashlib.sha256
        ).hexdigest()

    def set(self, key: str, value: str, expiration: int) -> None:
        self.key = self.secure_key(key)
        self.expiration = expiration
        cache.set(self.key, self.secure_value(value), expiration)

    def get(self, key: str) -> str | None:
        """
        Retrieve the stored HMAC digest for *key*.

        No decryption is provided — the returned value is already a digest.
        Use :meth:`validate` to compare an incoming plaintext value against it.

        Returns ``None`` when the key is absent or expired.
        """
        self.key = self.secure_key(key)
        value = cache.get(self.key)
        if not value:
            return None
        return value

    def delete(self, key: str) -> None:
        cache.delete(self.secure_key(key))
        self.key = ""
        self.expiration = 0

    def __str__(self) -> str:
        return self.key

    def __repr__(self) -> str:
        return self.key

    def __bool__(self) -> bool:
        return bool(self.key)

    def __len__(self) -> int:
        return len(self.key)

    def validate(self, key: str, value: str) -> bool:
        return self.secure_value(value) == self.get(key)
