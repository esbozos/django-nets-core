import json

import jwt
import requests
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.utils.translation import gettext as _
from oauth2_provider.models import Application

from nets_core.decorators import request_handler
from nets_core.models import UserDevice
from nets_core.params import RequestParam
from nets_core.responses import error_response, success_response
from nets_core.security import generate_tokens
from nets_core.tasks import get_google_avatar


User = get_user_model()


def _validate_client_credentials(client_id: str, client_secret: str):
    try:
        oauth_app = Application.objects.get(client_id=client_id)
    except Application.DoesNotExist:
        raise Exception(_("Invalid client_id"))

    if oauth_app.client_secret != client_secret:
        raise Exception(_("Invalid client_secret"))

    return oauth_app


def _create_or_update_user(profile: dict):
    email = (profile.get("email") or "").strip().lower()
    if not email:
        fallback = profile.get("provider_id")
        provider = profile.get("provider", "social")
        if not fallback:
            raise Exception(_("Provider did not return user email"))
        email = f"{provider}_{fallback}@social.local"

    user = User.objects.filter(email=email).first()
    if not user:
        user = User.objects.create(email=email)
        if hasattr(user, "set_unusable_password"):
            user.set_unusable_password()

    name = profile.get("name")
    given_name = profile.get("given_name")
    family_name = profile.get("family_name")

    if not given_name:
        given_name = name

    profile_fields_map = {
        "first_name": given_name,
        "last_name": family_name,
        "family_name": family_name,
        "full_name": name,
        "avatar": profile.get("picture"),
    }

    if not profile_fields_map["full_name"] and given_name:
        profile_fields_map["full_name"] = given_name

    for key, value in profile_fields_map.items():
        if value is not None and hasattr(user, key):
            setattr(user, key, value)

    user.save()
    user.refresh_from_db()
    return user


def _register_user_device(request, user):
    ua = getattr(request, "user_agent", None)
    uuid = None
    name = "unknown"

    if ua:
        uuid = getattr(ua, "device", None)
        if uuid:
            name = str(uuid)

    try:
        UserDevice.objects.create(user=user, name=name, uuid=uuid, ip=request.ip)
    except Exception:
        pass


def _oauth_login_response(request, user):
    oauth_app = _validate_client_credentials(
        request.params.client_id, request.params.client_secret
    )
    login(request, user, backend=settings.AUTHENTICATION_BACKENDS[0])

    tokens = generate_tokens(user, oauth_app)
    tokens["user"] = user.to_json()
    return success_response(tokens)


def _get_facebook_profile(token: str):
    response = requests.get(
        "https://graph.facebook.com/me",
        params={
            "fields": "id,name,first_name,last_name,email,picture.type(large)",
            "access_token": token,
        },
        timeout=10,
    )
    if response.status_code != 200:
        raise Exception(_("Invalid Facebook token"))

    data = response.json()
    picture_url = (
        (data.get("picture") or {}).get("data") or {}
    ).get("url")
    return {
        "provider": "facebook",
        "provider_id": data.get("id"),
        "email": data.get("email"),
        "name": data.get("name"),
        "given_name": data.get("first_name"),
        "family_name": data.get("last_name"),
        "picture": picture_url,
    }


def _get_google_profile(token: str):
    if not hasattr(settings, "GOOGLE_CLIENT_ID"):
        raise Exception(_("Google client id not set"))

    data = id_token.verify_oauth2_token(
        token, google_requests.Request(), settings.GOOGLE_CLIENT_ID
    )

    name = data.get("name")
    given_name = data.get("given_name")
    family_name = data.get("family_name")

    if not given_name:
        given_name = name

    return {
        "provider": "google",
        "provider_id": data.get("sub"),
        "email": data.get("email"),
        "name": name,
        "given_name": given_name,
        "family_name": family_name,
        "picture": data.get("picture"),
    }


def _get_microsoft_profile(token: str):
    response = requests.get(
        "https://graph.microsoft.com/v1.0/me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    if response.status_code != 200:
        raise Exception(_("Invalid Microsoft token"))

    data = response.json()
    return {
        "provider": "microsoft",
        "provider_id": data.get("id"),
        "email": data.get("mail") or data.get("userPrincipalName"),
        "name": data.get("displayName"),
        "given_name": data.get("givenName"),
        "family_name": data.get("surname"),
    }


def _get_github_profile(token: str):
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }

    profile_response = requests.get(
        "https://api.github.com/user", headers=headers, timeout=10
    )
    if profile_response.status_code != 200:
        raise Exception(_("Invalid GitHub token"))

    data = profile_response.json()
    email = data.get("email")
    if not email:
        emails_response = requests.get(
            "https://api.github.com/user/emails", headers=headers, timeout=10
        )
        if emails_response.status_code == 200:
            emails = emails_response.json()
            primary_verified = next(
                (
                    e.get("email")
                    for e in emails
                    if e.get("primary") and e.get("verified")
                ),
                None,
            )
            email = primary_verified or (emails[0].get("email") if emails else None)

    full_name = data.get("name") or data.get("login")
    return {
        "provider": "github",
        "provider_id": str(data.get("id")) if data.get("id") else data.get("login"),
        "email": email,
        "name": full_name,
        "given_name": full_name,
        "picture": data.get("avatar_url"),
    }


def _get_apple_public_key(identity_token: str):
    unverified_header = jwt.get_unverified_header(identity_token)
    keys_response = requests.get("https://appleid.apple.com/auth/keys", timeout=10)
    if keys_response.status_code != 200:
        raise Exception(_("Unable to validate Apple token"))

    keys = keys_response.json().get("keys", [])
    kid = unverified_header.get("kid")
    key_data = next((k for k in keys if k.get("kid") == kid), None)
    if not key_data:
        raise Exception(_("Invalid Apple token key"))

    return jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key_data))


def _get_apple_profile(token: str):
    if not hasattr(settings, "APPLE_CLIENT_ID"):
        raise Exception(_("Apple client id not set"))

    public_key = _get_apple_public_key(token)
    data = jwt.decode(
        token,
        key=public_key,
        algorithms=["RS256"],
        audience=settings.APPLE_CLIENT_ID,
        issuer="https://appleid.apple.com",
    )

    return {
        "provider": "apple",
        "provider_id": data.get("sub"),
        "email": data.get("email"),
        "name": data.get("email"),
        "given_name": data.get("email"),
    }


def _social_login(request, profile_getter):
    profile = profile_getter(request.params.token)
    user = _create_or_update_user(profile)

    _register_user_device(request, user)

    if profile.get("picture"):
        get_google_avatar.delay(user.id, profile["picture"])

    return _oauth_login_response(request, user)


@request_handler(
    path="loginWithApple/",
    name="loginWithApple",
    method="POST",
    params=[
        RequestParam("token", type=str),
        RequestParam("client_id", type=str),
        RequestParam("client_secret", type=str),
    ],
    public=True,
)
def login_with_apple(request):
    try:
        return _social_login(request, _get_apple_profile)
    except Exception as e:
        return error_response(e.__str__())


@request_handler(
    path="loginWithFacebook/",
    name="loginWithFacebook",
    method="POST",
    params=[
        RequestParam("token", type=str),
        RequestParam("client_id", type=str),
        RequestParam("client_secret", type=str),
    ],
    public=True,
)
def login_with_facebook(request):
    try:
        return _social_login(request, _get_facebook_profile)
    except Exception as e:
        return error_response(e.__str__())


@request_handler(
    path="loginWithMicrosoft/",
    name="loginWithMicrosoft",
    method="POST",
    params=[
        RequestParam("token", type=str),
        RequestParam("client_id", type=str),
        RequestParam("client_secret", type=str),
    ],
    public=True,
)
def login_with_microsoft(request):
    try:
        return _social_login(request, _get_microsoft_profile)
    except Exception as e:
        return error_response(e.__str__())


@request_handler(
    path="loginWithGithub/",
    name="loginWithGithub",
    method="POST",
    params=[
        RequestParam("token", type=str),
        RequestParam("client_id", type=str),
        RequestParam("client_secret", type=str),
    ],
    public=True,
)
def login_with_github(request):
    try:
        return _social_login(request, _get_github_profile)
    except Exception as e:
        return error_response(e.__str__())


@request_handler(
    path="loginWithGoogleSocial/",
    name="loginWithGoogleSocial",
    method="POST",
    params=[
        RequestParam("token", type=str),
        RequestParam("client_id", type=str),
        RequestParam("client_secret", type=str),
    ],
    public=True,
)
def login_with_google_social(request):
    try:
        return _social_login(request, _get_google_profile)
    except Exception as e:
        return error_response(e.__str__())
