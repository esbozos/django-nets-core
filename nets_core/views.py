from datetime import timedelta
from django.core.mail import EmailMultiAlternatives
from django.db.utils import IntegrityError
from django.shortcuts import render
import logging
from django.utils.translation import gettext_lazy as _
from nets_core.decorators import request_handler
from nets_core.models import VerificationCode
from nets_core.params import RequestParam
from nets_core.responses import error_response, success_response
from nets_core.security import authenticate
from django.contrib.auth import login, logout
from django.utils import timezone
from django.conf import settings
from oauth2_provider.models import Application, AccessToken, RefreshToken
from oauthlib import common
from django.contrib.auth import get_user_model

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
    ],
)
def auth_login(request):

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
            **{username_field: getattr(request.params, username_field)}, defaults=defaults
        )

        if not created:
            # Verification code is created on new_user created
            # then create new VerificationCode, nets_core listeners
            # dispatch the email and handle all automatically

            VerificationCode.objects.create(user=new_user)

        return success_response(_("CODE SENT"))

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
    try:
        tokens = authenticate(
            user=user,
            code=request.params.code,
            client_id=request.params.client_id,
            client_secret=request.params.client_secret,
        )
        if not user.email_verified:
            user.email_verified = True
        user.last_login = timezone.now()
        user.save()
        tokens.update({"user": user.to_json()})

        return success_response(tokens)

    except Exception as e:
        msg = e.__str__()
        return error_response(msg)


@request_handler()
def auth_logout(request):
    logout(request)
    return success_response(_("Logged out successfully"))


@request_handler()
def auth_get_profile(request):
    request.user.save()
    return success_response(request.user.to_json())


@request_handler()
def update_user(request):
    user = request.user
    updated_fields = {}

    if hasattr(user, 'updated_fields'):
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
                        "old": getattr(user, key),
                        "new": val,
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
