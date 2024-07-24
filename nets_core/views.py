from datetime import timedelta
from django.core.mail import EmailMultiAlternatives
from django.db.utils import IntegrityError
from django.http import HttpResponse
from django.shortcuts import render
import logging
from django.utils.translation import gettext_lazy as _
from nets_core.decorators import request_handler
from nets_core.models import UserDevice, VerificationCode
from nets_core.params import RequestParam
from nets_core.responses import error_response, success_response
from nets_core.security import authenticate
from django.contrib.auth import login, logout
from django.utils import timezone
from django.conf import settings
from oauth2_provider.models import Application, AccessToken, RefreshToken
from oauthlib import common
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured

User = get_user_model()
username_field = getattr(User, "USERNAME_FIELD", "username")

logger = logging.getLogger(__name__)

prohibited_fields = [
    "password",
    "is_superuser",
    "is_staff",
    "is_active",
    "verified",
    "email_verified",
    "last_login",
    "date_joined",
    "updated_fields",
    "groups",
    "user_permissions",
    "doc_*",
]
try:
    if settings.NETS_CORE_USER_PROHIBITED_FIELDS:
        prohibited_fields += settings.NETS_CORE_USER_PROHIBITED_FIELDS
except:
    pass


def valid_gender(s):
    return s in ["male", "female", "other", "_"]


@request_handler(
    public=True,
    params=[
        RequestParam(username_field, str),
        RequestParam("device", dict, True, default=None),
    ],
)
def auth_login(request):
    print(request.params)
    try:
        defaults = {}
        for key, val in request.params._asdict().items():
            if hasattr(User, key):
                for field in prohibited_fields:
                    if field in key:
                        # exact match e.g. password
                        logger.info(f"Prohibited field {key} found in auth request")
                        continue
                    if field.endswith("*"):
                        # check if key starts with field
                        # e.g. doc_id, doc_id_type, doc_id_country
                        if key.startswith(field[:-1]):
                            logger.info(f"Prohibited field {key} found in auth request")
                            continue

                defaults[key] = val

        new_user, created = User.objects.get_or_create(
            **{username_field: getattr(request.params, username_field)},
            defaults=defaults,
        )

        device = None

        if hasattr(request.params, "device") and request.params.device is not None:
            valid_device_fields = [
                "name",
                "os",
                "os_version",
                "device_token",
                "firebase_token",
                "app_version",
                "device_id",
                "device_type",
            ]
            device_data = {}

            for key, val in request.params.device.items():
                if key in valid_device_fields:
                    device_data[key] = val

            if "uuid" in request.params.device and request.params.device["uuid"]:
                logger.info(
                    f"Device uuid {request.params.device['uuid']} found in auth request"
                )
                try:
                    device = UserDevice.objects.get(
                        uuid=request.params.device["uuid"], user=new_user
                    )

                    for key, val in device_data.items():
                        setattr(device, key, val)
                    device.save()

                    # TODO: Notification to user to new login from device

                except UserDevice.DoesNotExist:
                    # uuid does not exist or is not associated with user
                    # delete user if created as invalid request is made
                    logger.warning(
                        f"Invalid device uuid {request.params.device['uuid']} found in auth request from user request {request.params}"
                    )
                    if created:
                        new_user.delete()

                    return error_response(_("Invalid device uuid"), 400)
            else:
                # new device
                device_data["user"] = new_user
                if "firebase_token" in device_data:
                    device = UserDevice.objects.filter(
                        firebase_token=device_data["firebase_token"], user=new_user
                    )
                    if device.exists():
                        device = device.first()
                        for key, val in device_data.items():
                            setattr(device, key, val)
                        device.save()
                    else:
                        device = UserDevice.objects.create(**device_data)
                else:
                    device = UserDevice.objects.create(**device_data)

        # create verification code, listeners will send email/sms and devices notifications
        # with firebase
        VerificationCode.objects.create(user=new_user, ip=request.ip, device=device)

        return success_response(
            _("CODE SENT"),
            extra={
                "device_uuid": device.uuid if device else None,
            },
        )

    except IntegrityError as e:
        print(e)
        return error_response(_("Username not available"), 400)

    except Exception as e:
        msg = e.__str__()
        return error_response(msg)


@request_handler(params=[RequestParam("email", "email")], public=True)
def check_email(request):
    print(request.params.email)
    exists = False
    print(exists)
    return success_response(exists)


@request_handler(
    User,
    index_field=username_field,
    params=[
        RequestParam(username_field, str),
        RequestParam("code", int),
        RequestParam("client_id", str),
        RequestParam("client_secret", str),
    ],
    public=True,
)
def auth(request):
    user = request.obj
    device_uuid = None
    if hasattr(request.params, "device_uuid") and request.params.device_uuid:
        try:
            device = UserDevice.objects.get(uuid=request.params.device_uuid, user=user)
            device_uuid = device.uuid
        except UserDevice.DoesNotExist:
            return error_response(_("Invalid device uuid"), 400)

    try:
        tokens = authenticate(
            user=user,
            code=request.params.code,
            client_id=request.params.client_id,
            client_secret=request.params.client_secret,
            device_uuid=device_uuid,
        )
        if hasattr(user, "email_verified") and not user.email_verified:
            user.email_verified = True
        user.last_login = timezone.now()
        user.save()
        tokens.update({"user": user.to_json()})
        # add user to session
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return success_response(tokens)

    except Exception as e:
        msg = e.__str__()
        return error_response(msg)


@request_handler()
def auth_logout(request):
    params = request.params
    if hasattr(params, "device_uuid"):
        try:
            device = UserDevice.objects.get(uuid=params.device_uuid, user=request.user)
            device.delete()
        except UserDevice.DoesNotExist:
            pass
    # get Bearer token
    try:
        access_token = request.headers["Authorization"].split(" ")[1]
        token = AccessToken.objects.get(token=access_token)
        token.delete()
        refresh_token = RefreshToken.objects.get(access_token=token)
        refresh_token.delete()
    except Exception as e:
        pass

    logout(request)
    return success_response(_("Logged out successfully"))


@request_handler(
    params=[
        RequestParam("fields", list, True, default=None),
    ]
)
def auth_get_profile(request):
    request.user.save()
    fields = request.params.fields
    # convert list in tuple
    if fields:
        fields = tuple(fields)

    return success_response(request.user.to_json(fields=fields))


@request_handler()
def update_user(request):
    user = request.user
    updated_fields = {}

    if hasattr(user, "updated_fields"):
        updated_fields = user.updated_fields

    for key, val in request.params._asdict().items():
        if hasattr(user, key):
            for field in prohibited_fields:
                if field in key:
                    # exact match e.g. password
                    logger.info(f"Prohibited field {key} found in auth request")
                    continue

                if field.endswith("*"):
                    # check if key starts with field
                    # e.g. doc_id, doc_id_type, doc_id_country
                    if key.startswith(field[:-1]):
                        # logger.info(f"Prohibited field {key} found in auth request")
                        continue

            if key not in updated_fields:
                updated_fields[key] = []
            updated_fields[key].append(
                {
                    "old": str(getattr(user, key)),
                    "new": str(val),
                    "time": timezone.now().__str__(),
                }
            )
            setattr(user, key, val)

    if request.FILES:
        for field in request.FILES:
            if not hasattr(user, field):
                continue

            for field in prohibited_fields:
                if field in key:
                    # exact match e.g. password
                    logger.info(f"Prohibited field {key} found in auth request")
                    continue

                if field.endswith("*"):
                    # check if key starts with field
                    # e.g. doc_id, doc_id_type, doc_id_country
                    if key.startswith(field[:-1]):
                        # logger.info(f"Prohibited field {key} found in auth request")
                        continue

                if field not in updated_fields:
                    updated_fields[field] = []
                updated_fields[field].append(
                    {
                        "old": str(getattr(user, field)),
                        "new": str(request.FILES[field]),
                        "time": timezone.now().__str__(),
                    }
                )

                setattr(user, field, request.FILES[field])

    user.updated_fields = updated_fields
    try:
        user.save()
    except Exception as e:
        return error_response(e.__str__())

    return success_response(user.to_json())


@request_handler(public=True)
def request_delete_user_account(request):
    if not hasattr(settings, "NETS_CORE_DELETE_ACCOUNT_TEMPLATE"):
        info_template = "nets_core/delete_account_info.html"
    else:
        info_template = settings.NETS_CORE_DELETE_ACCOUNT_TEMPLATE

    return render(
        request,
        "nets_core/delete_account.html",
        {
            "title": _("Delete Account"),
            "info_template": info_template,
            "user": request.user,
        },
    )


@request_handler(
    params=[RequestParam("sure", bool, default=False), RequestParam("code", str)],
)
def delete_user_account(request):
    if not request.params.sure:
        return error_response(_("Are you sure?"), 400)

    if not request.params.code:
        return error_response(_("Invalid code"), 400)

    try:
        code = (
            VerificationCode.objects.get(user=request.user, verified=False)
            .order_by("-created")
            .first()
        )

        if code.validate(request.params.code):
            # delete user
            user = request.user
            user.delete()
            return success_response(_("Account deleted successfully"))

    except VerificationCode.DoesNotExist:
        return error_response(_("Invalid code"), 400)

    except Exception as e:
        return error_response(e.__str__())

    return error_response(_("Invalid code"), 400)
