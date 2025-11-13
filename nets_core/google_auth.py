from google.oauth2 import id_token
from google.auth.transport import requests

from django.http import JsonResponse
from django.conf import settings
from oauth2_provider.models import Application

# from nets_user.models import User, MobilePhone
from django.contrib.auth import login
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _

from oauth2_provider.models import Application, AccessToken, RefreshToken

from nets_core.params import RequestParam
from nets_core.models import UserDevice, VerificationCode
from nets_core.security import authenticate, generate_tokens
from nets_core.responses import error_response, success_response
from nets_core.decorators import request_handler
from nets_core.tasks import get_google_avatar




User = get_user_model()
username_field = getattr(User, "USERNAME_FIELD", "username")

# from nets_user.tasks import add_user_device, log_useraction, get_google_avatar
# from nets_user.utils import create_access_token


@request_handler(
    params=[
        RequestParam("token", type=str),
        RequestParam("client_id",  type=str),
        RequestParam("client_secret", type=str),
        
    ],
    public=True,
)
def login_with_google(request):
    if not hasattr(settings, "GOOGLE_CLIENT_ID"):
        return JsonResponse(
            {"res": 0, "message": "Google client id not set"}, status=500
        )

    try:
        idinfo = id_token.verify_oauth2_token(
            request.params.token, requests.Request(), settings.GOOGLE_CLIENT_ID
        )
        email = idinfo["email"]
        print(idinfo)
        user = User.objects.filter(email=email).first()
        if not user:
            name = idinfo["name"]
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
            # first_name=given_name,
            #     dob=dob,
            #     gender=gender,
            #     last_name=family_name,
            if hasattr(user, "set_unusable_password"):
                user.set_unusable_password()
                
            profile_fields_map = {
                "first_name": name,
                "last_name": given_name,
                "dob": dob,
                "gender": gender,
                "family_name": family_name,
                "full_name": f"{name} {given_name}",
                "phone": phone,
                "avatar": idinfo.get("picture", None),
            }
            for k, v in profile_fields_map.items():
                if hasattr(user, k):
                    setattr(user, k, v)
                         
            user.save()
            user.refresh_from_db()

        ua = request.user_agent
        uuid = ua.device
        name = uuid

        next_url = "/app"
        try:
            device = UserDevice.objects.create(
                user=user, name=name, uuid=uuid, ip=request.ip
            )
        except Exception as e:
            pass
        # add_user_device.delay(uuid, name, user.id, request.ip)
        # log_useraction.delay(
        #     f"Ingresó al sistema a través de {name} con Google", user.id, request.ip
        # )
        login(request, user, backend=settings.AUTHENTICATION_BACKENDS[0])
        try:
            application = Application.objects.get(client_id=request.params.client_id)
        except Application.DoesNotExist:
            if settings.DEBUG:
                application = Application.objects.first()
            else:
                return JsonResponse(
                    {"res": 0, "message": "Invalid arkadu client id"}, status=400
                )


        # get avatar
        if "picture" in idinfo:
            get_google_avatar.delay(user.id, idinfo["picture"])

        client_id = request.params.client_id
        client_secret = request.params.client_secret
        
        try:
            oauth_app = Application.objects.get(client_id=client_id)
            if not oauth_app.client_secret == client_secret:
                raise Exception(_("Invalid client_secret"))
            
            tokens = generate_tokens(user, oauth_app)
            tokens["user"] = user.to_json(mode="full")
            return success_response(tokens)
        except Application.DoesNotExist:
            raise Exception(_("Invalid client_id"))
        except Exception as e:
            raise Exception(e)
        
        # return JsonResponse(
        #     {
        #         "res": 1,
        #         "message": "ok",
        #         "user": user.to_json(mode="full"),
        #         "access_token": access_token.token,
        #         "refresh_token": refresh_token.token,
        #         "token_expires": access_token.expires,
        #     }
        # )

    except ValueError as e:
        return JsonResponse({"res": 0, "message": "Invalid token"})
    except Exception as e:
        print(e)
        return JsonResponse({"res": 0, "message": e.__str__()})
