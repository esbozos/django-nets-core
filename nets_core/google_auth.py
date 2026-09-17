from google.oauth2 import id_token
from google.auth.transport import requests

from django.conf import settings
from django.contrib.auth import login, get_user_model
from django.utils.translation import gettext as _
from oauth2_provider.models import Application

from nets_core.params import RequestParam
from nets_core.models import UserDevice
from nets_core.security import generate_tokens
from nets_core.responses import error_response, success_response
from nets_core.decorators import request_handler
from nets_core.tasks import get_google_avatar


User = get_user_model()
username_field = getattr(User, "USERNAME_FIELD", "username")


@request_handler(
    path="loginWithGoogle/",
    name="loginWithGoogle",
    method="POST",
    params=[
        RequestParam("token", type=str),
        RequestParam("client_id", type=str),
        RequestParam("client_secret", type=str),
    ],
    public=True,
)
def login_with_google(request):
    if not hasattr(settings, "GOOGLE_CLIENT_ID"):
        return error_response(_("Google client id not set"))

    try:
        idinfo = id_token.verify_oauth2_token(
            request.params.token, requests.Request(), settings.GOOGLE_CLIENT_ID
        )
        email = idinfo["email"]
        user = User.objects.filter(email=email).first()
        if not user:
            name = idinfo.get("name", "")
            given_name = idinfo.get("given_name", None)
            family_name = idinfo.get("family_name", None)
            if not given_name:
                given_name = name
            dob = idinfo.get("dob", None)
            phone = idinfo.get("phone", None)
            gender = idinfo.get("gender", "other")
            user = User.objects.create(
                email=email,
            )
            if hasattr(user, "set_unusable_password"):
                user.set_unusable_password()

            profile_fields_map = {
                "first_name": name,
                "last_name": given_name,
                "dob": dob,
                "gender": gender,
                "family_name": family_name,
                "full_name": f"{name} {given_name}".strip(),
                "phone": phone,
                "avatar": idinfo.get("picture", None),
            }
            for k, v in profile_fields_map.items():
                if hasattr(user, k):
                    setattr(user, k, v)

            user.save()
            user.refresh_from_db()

        ua = getattr(request, "user_agent", None)
        uuid = getattr(ua, "device", None) if ua else None
        name = str(uuid) if uuid else "unknown"
        ip = getattr(request, "ip", None) or getattr(request, "META", {}).get("REMOTE_ADDR")

        try:
            UserDevice.objects.create(
                user=user, name=name, uuid=uuid, ip=ip
            )
        except Exception:
            pass

        login(request, user, backend=settings.AUTHENTICATION_BACKENDS[0])

        client_id = request.params.client_id
        client_secret = request.params.client_secret

        try:
            oauth_app = Application.objects.get(client_id=client_id)
        except Application.DoesNotExist:
            if settings.DEBUG:
                oauth_app = Application.objects.first()
            else:
                return error_response(_("Invalid client_id"))

        if oauth_app.client_secret != client_secret:
            return error_response(_("Invalid client_secret"))

        # get avatar
        if "picture" in idinfo and idinfo["picture"]:
            get_google_avatar.delay(user.id, idinfo["picture"])

        tokens = generate_tokens(user, oauth_app)
        tokens["user"] = user.to_json()
        return success_response(tokens)

    except ValueError:
        return error_response(_("Invalid token"))
    except Exception as e:
        return error_response(str(e))
