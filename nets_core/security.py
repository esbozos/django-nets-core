import hmac
import hashlib
from django.apps import apps
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.contrib.auth.hashers import check_password, make_password
from base64 import b64decode, b64encode
from oauthlib import common
from oauth2_provider.models import Application, AccessToken, RefreshToken

# TODO: create middleware to restring token_access with device_uuid


def validate_verification_code(user, code: str) -> bool:
    """
    Validate verification code for user
    Parameters:
    user (instance): Instance of settings.AUTH_MODEL_MODEL
    code (str): Verification code

    Returns:
    bool: True if code is valid, False otherwise

    """
    try:
        from nets_core.models import VerificationCode
    except:
        raise Exception(_("nets_core.models not found"))
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
    except:
        raise Exception(_("nets_core.models not found"))
    
    try:
        oauth_app = Application.objects.get(client_id=client_id)
        if not oauth_app.client_secret == client_secret:
            raise Exception(_("Invalid client_secret"))
    except Application.DoesNotExist:
        raise Exception(_("Invalid client_id"))

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
    expire_seconds = 60 * 60 * 24 * 30  # 30 days as default
    try:
        expire_seconds = settings.ACCESS_TOKEN_EXPIRE_SECONDS
    except:
        pass

    expires = timezone.now() + timezone.timedelta(seconds=expire_seconds)

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
    Create a role for project to provide multi project support
    Parameters:
    project (instance): Project instance. Should be the same as settings.NETS_CORE_PROJECT_MODEL
    role_name (str): Role name

    Returns:
    instance: nets_core.models.Role

    """
    try:
        from nets_core.models import Role

    except:
        raise Exception(_("nets_core.models not found"))
    
    try:
        project_model = apps.get_model(settings.NETS_CORE_PROJECT_MODEL)
        if not isinstance(project, project_model):
            raise Exception(
                _(
                    "Invalid project instance. Should be the same as settings.NETS_CORE_PROJECT_MODEL"
                )
            )

    except project_model.DoesNotExist:
        raise Exception(
            _(
                "Invalid project instance. Should be the same as settings.NETS_CORE_PROJECT_MODEL"
            )
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
    Create a role for project to provide multi project support
    Parameters:
    project (instance): Project instance. Should be the same as settings.NETS_CORE_PROJECT_MODEL
    role_name (str): Role name
    codename (str): Permission codename

    Returns:
    instance: nets_core.models.Role

    """
    try:
        from nets_core.models import Permission
    except:
        raise Exception(_("nets_core.models not found"))
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
    Add role to user in project
    Parameters:
    user (instance): User instance. Should be the same as settings.AUTH_USER_MODEL
    project (instance): Project instance. Should be the same as settings.NETS_CORE_PROJECT_MODEL
    role_name (str): Role name

    Returns:
    instance: nets_core.models.Role

    """
    try:
        from nets_core.models import UserRole
    except:
        raise Exception(_("nets_core.models not found"))
    
    try:
        project_model = apps.get_model(settings.NETS_CORE_PROJECT_MODEL)
        if not isinstance(project, project_model):
            raise Exception(
                _(
                    "Invalid project instance. Should be the same as settings.NETS_CORE_PROJECT_MODEL"
                )
            )

        user_model = apps.get_model(settings.AUTH_USER_MODEL)
        if not isinstance(user, user_model):
            raise Exception(
                _(
                    "Invalid user instance. Should be the same as settings.AUTH_USER_MODEL"
                )
            )

    except project_model.DoesNotExist:
        raise Exception(
            _(
                "Invalid project instance. Should be the same as settings.NETS_CORE_PROJECT_MODEL"
            )
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
    Secure cache to store and retrieve data with expiration time.
    This cache is secure because it uses the same key to store and retrieve data.
    It uses the same key to store and retrieve data.
    This cache
    Parameters:
    key (str): Key to store and retrieve data
    expiration (int): Time in seconds to expire data

    Returns:
    instance: SecureCache

    """

    def __init__(self):
        self.key = ""
        self.expiration = 0

    def secure_key(self, key: str) -> str:
        key_prefix = "NETS_SK_"
        # use settings.NETS_CORE_SECURE_CACHE_KEY or settings.SECRET_KEY as secret key
        secret_key = getattr(
            settings, "NETS_CORE_SECURE_CACHE_KEY", settings.SECRET_KEY
        )
        key = hmac.new(
            secret_key.encode("utf-8"), key.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        k = f"{key_prefix}{key}"
        if len(k) > 250:
            k = k[:250]
        return k

    def secure_value(self, value: str) -> str: 
        # use settings.NETS_CORE_SECURE_CACHE_KEY or settings.SECRET_KEY as secret key
        secret_key = getattr(
            settings, "NETS_CORE_SECURE_CACHE_KEY", settings.SECRET_KEY
        )
        value = hmac.new(
            secret_key.encode("utf-8"), value.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        return value

    def set(self, key: str, value: str, expiration: int) -> None:
        self.key = self.secure_key(key)
        self.expiration = expiration
        cache.set(self.key, self.secure_value(value), expiration)

    def get(self, key: str) -> str | None:
        """
        Get encrypted value from cache
        No decryption provided. Use secure_value to compare values
        Parameters:
        key (str): Key to get value

        Returns:
        str: Value or None if not found

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
