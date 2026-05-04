Django NETS CORE
================

Production-oriented toolkit for Django APIs with built-in request validation,
OTP authentication, OAuth2 token issuance, project-scoped permissions,
email delivery, push notifications, and social login providers.

Overview
--------

NETS CORE reduces boilerplate across common backend concerns:

- Input validation and coercion for API payloads.
- Authentication flows with verification codes and OAuth2 tokens.
- Social login onboarding.
- Role and permission management (global and project-scoped).
- User device tracking.
- Email and push notification integration.
- Model serialization patterns with protected fields support.

What Is Included
----------------

Core API endpoints are exposed through auth URLs:

- POST /login/
- POST /authenticate/
- POST /logout/
- POST /update/
- GET/POST /getProfile/
- GET/POST /requestDelete/
- POST /delete/
- GET /openapi.json

Social login endpoints:

- POST /loginWithGoogle/ (legacy endpoint kept for compatibility)
- POST /loginWithGoogleSocial/ (new unified flow)
- POST /loginWithApple/
- POST /loginWithFacebook/
- POST /loginWithMicrosoft/
- POST /loginWithGithub/

Built-in models:

- NetsCoreBaseModel
- OwnedModel
- Permission
- Role
- RolePermission
- UserRole
- VerificationCode
- UserDevice
- EmailTemplate
- CustomEmail
- EmailNotification
- UserFirebaseNotification

Built-in helpers/services:

- request_handler decorator and RequestParam parser.
- Declarative endpoint routing metadata (path/url + name) for auto URL generation.
- Optional HTTP method guards (method/methods) with 405 + Allow header.
- Token generation/authentication helpers.
- SecureCache: HMAC-backed cache for storing and validating short-lived secrets.
- ``get_upload_path``: model-aware ``upload_to`` callable for organised file storage.
- ``check_perm`` / role and permission management helpers.
- ``get_client_ip``: reverse-proxy-aware IP extraction.
- Email sending service with queue/immediate modes.
- Firebase push helpers.
- Settings bootstrap command.

Installation
------------

.. code-block:: bash

    pip install django-nets-core

Dependencies are installed automatically from package metadata. Current notable
runtime dependencies include Django, django-oauth-toolkit, google-auth,
PyJWT, Celery, channels, channels-redis, firebase-admin, and cache backends.

Minimal Integration
-------------------

1. Add required apps:

.. code-block:: python

    INSTALLED_APPS = [
        # ...
        "oauth2_provider",
        "nets_core",
    ]

2. Add URL routes:

.. code-block:: python

    from django.urls import include, path

    urlpatterns = [
        path("", include("nets_core.auth_urls", namespace="auth")),
    ]

3. Configure authentication backends:

.. code-block:: python

    AUTHENTICATION_BACKENDS = [
        "oauth2_provider.backends.OAuth2Backend",
        "django.contrib.auth.backends.ModelBackend",
    ]

4. Configure cache (required for verification code behavior in production):

.. code-block:: python

    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.memcached.PyMemcacheCache",
            "LOCATION": "127.0.0.1:11211",
        }
    }

5. Run migrations:

.. code-block:: bash

    python manage.py migrate

6. Validate/setup baseline settings:

.. code-block:: bash

    python manage.py nets-settings

Management Commands
-------------------

Check configuration:

.. code-block:: bash

    python manage.py nets-settings

Generate/update baseline settings files:

.. code-block:: bash

    python manage.py nets-settings --create
    python manage.py nets-settings --create --force

Push notification test helper:

.. code-block:: bash

    python manage.py test_push_notification

Authentication
--------------

OTP Login Flow
^^^^^^^^^^^^^^

Step 1: request verification code (creates/updates user and device).

Endpoint:

- POST /login/

Parameters:

- User.USERNAME_FIELD (for example email or username, depending on your custom User model)
- device (dict; should include device metadata)

Supported device keys (current implementation):

- name
- os
- os_version
- device_token
- firebase_token
- app_version
- device_id
- device_type
- uuid (optional, for updating an existing device)

Example:

.. code-block:: json

    {
      "email": "user@example.com",
      "device": {
        "name": "Pixel 8",
        "os": "Android",
        "os_version": "15",
        "firebase_token": "fcm_token",
        "app_version": "1.0.0"
      }
    }

Response:

.. code-block:: json

    {
      "res": 1,
      "data": "CODE SENT",
      "extra": {
        "device_uuid": "..."
      }
    }

Step 2: authenticate code and issue OAuth tokens.

Endpoint:

- POST /authenticate/

Parameters:

- User.USERNAME_FIELD
- code
- client_id
- client_secret
- device_uuid (optional but recommended when device-bound verification is used)

Response:

.. code-block:: json

    {
      "res": 1,
      "data": {
        "access_token": "...",
        "refresh_token": "...",
        "token_expire": "...",
        "user": {
          "...": "..."
        }
      }
    }

Logout
^^^^^^

Endpoint:

- POST /logout/

Behavior:

- Removes device if device_uuid is sent.
- Deletes OAuth access token from Authorization header when present.
- Clears Django session.

Using the authenticate helper directly
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you want to build a custom endpoint flow, you can call the helper in
nets_core.security:

.. code-block:: python

    from nets_core.security import authenticate

    tokens = authenticate(
        user=user,
        code="123456",
        client_id="your_client_id",
        client_secret="your_client_secret",
        device_uuid=device_uuid,  # optional
    )

Social Login
^^^^^^^^^^^^

Unified provider flow is implemented in social_auth with provider-specific
validation and a shared local user/token creation path.

Common social request payload:

.. code-block:: json

    {
      "token": "provider_token",
      "client_id": "oauth_application_client_id",
      "client_secret": "oauth_application_client_secret"
    }

Provider-specific notes:

- Google: validates ID token against GOOGLE_CLIENT_ID.
- Apple: verifies JWT signature against Apple JWKs and validates audience with APPLE_CLIENT_ID.
- Facebook: validates via Graph API /me.
- Microsoft: validates via Microsoft Graph /me.
- GitHub: validates via /user and /user/emails.

Compatibility note:

- /loginWithGoogle/ remains available from legacy module for existing clients.
- /loginWithGoogleSocial/ is the recommended new endpoint.

Authorization and Project Permissions
-------------------------------------

Permission Model
^^^^^^^^^^^^^^^^

NETS CORE includes first-class authorization entities:

- Permission(codename)
- Role
- RolePermission
- UserRole

Additionally, role assignments can be project-scoped through generic relation
fields (project_content_type/project_id).

Enable Project-Aware Authorization
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Set these settings to enable project and membership resolution in handlers:

.. code-block:: python

    NETS_CORE_PROJECT_MODEL = "myapp.MyProject"
    NETS_CORE_PROJECT_MEMBER_MODEL = "myapp.MyProjectMember"

Recommended model pattern:

.. code-block:: python

    from django.db import models
    from nets_core.models import OwnedModel

    class MyProject(OwnedModel):
        name = models.CharField(max_length=255)
        enabled = models.BooleanField(default=True)
        description = models.TextField(blank=True, null=True)

        JSON_DATA_FIELDS = ("id", "name", "enabled", "description", "created", "updated")
        PROTECTED_FIELDS = ["user"]

        def __str__(self):
            return self.name


    class MyProjectMember(OwnedModel):
        project = models.ForeignKey(MyProject, on_delete=models.CASCADE)
        enabled = models.BooleanField(default=True)
        is_superuser = models.BooleanField(default=False)

        # Optional: role attribute used by your own access logic.
        # You can use either your custom field or relate to nets_core Role.
        role = models.CharField(max_length=50, default="member")

        JSON_DATA_FIELDS = ("id", "project_id", "user_id", "enabled", "is_superuser", "role")
        PROTECTED_FIELDS = ["project", "is_superuser"]

        def __str__(self):
            return f"{self.user} - {self.project}"

Using Permissions in Endpoints
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use request_handler can_do and perm_required to gate access:

.. code-block:: python

    from django.http import JsonResponse
    from nets_core.decorators import request_handler
    from nets_core.params import RequestParam

    @request_handler(
        params=[RequestParam("project_id", int)],
        can_do="myapp.can_change_project",
        perm_required=True,
        project_required=True,
    )
    def update_project(request):
        return JsonResponse({"res": 1})

Notes:

- If permission codename does not exist, NETS CORE can create it and deny the first call.
- project_id in request payload is used to resolve project context.
- Ownership checks apply when object-based handlers are used.

Utility helpers in security module:

- get_or_create_project_role
- get_or_create_project_role_permission
- add_user_to_role

Model Extension and Serialization
---------------------------------

NetsCoreBaseModel
^^^^^^^^^^^^^^^^^

Provides:

- created and updated timestamps.
- updated_fields JSON history.
- to_json(fields=...) serialization helper.

OwnedModel
^^^^^^^^^^

Extends NetsCoreBaseModel and adds:

- user ForeignKey ownership.

Defining JSON output
^^^^^^^^^^^^^^^^^^^^

You should define JSON_DATA_FIELDS in your models to make to_json() predictable.

.. code-block:: python

    class Invoice(OwnedModel):
        total = models.DecimalField(max_digits=10, decimal_places=2)
        JSON_DATA_FIELDS = ("id", "user_id", "total", "created")

Protecting sensitive fields
^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Model-level: PROTECTED_FIELDS in each model.
- Global-level: NETS_CORE_PROTECTED_FIELDS setting.

Authentication endpoints also honor NETS_CORE_USER_PROHIBITED_FIELDS for user
profile updates.

request_handler and RequestParam
--------------------------------

request_handler features:

- csrf_exempt wrapping.
- Authentication/public checks.
- Parameter parsing and type casting.
- Optional permission checks.
- Optional object lookup with owner-aware access controls.
- project/project_membership resolution via project_id.
- Optional declarative route metadata: path (or url) and name.
- Optional HTTP method guards with method or methods.

RequestParam supports:

- Python types: str, int, bool, float, list, dict.
- Named types: date, datetime, email, file.
- Optional defaults and custom validate callbacks.

Example:

.. code-block:: python

    from nets_core.params import RequestParam

    params = [
        RequestParam("title", str),
        RequestParam("published", bool, optional=True, default=False),
        RequestParam("publish_at", "datetime", optional=True),
        RequestParam("cover", "file", optional=True),
    ]

Declarative routes and method guards:

.. code-block:: python

    from nets_core.decorators import request_handler
    from nets_core.routing import (
        build_openapi_paths,
        build_route_registry,
        build_urlpatterns,
    )

    @request_handler(
        public=True,
        path="health/",
        name="health",
        methods=["GET"],
    )
    def health(request):
        return JsonResponse({"res": 1, "data": "ok"})

    urlpatterns = [
        *build_urlpatterns("myapp.views"),
    ]

    # Useful for docs pages or custom tooling
    route_registry = build_route_registry("myapp.views")

    # Drop-in OpenAPI `paths` object
    openapi_paths = build_openapi_paths("myapp.views", tags=["auth"])

Notes:

- method is a convenience alias for a single HTTP verb.
- methods accepts one or many verbs (GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS).
- If a method is not allowed, request_handler returns 405 and sets the Allow header.
- build_route_registry returns normalized route metadata (path, name, methods, module, view_name).
- build_openapi_paths returns a valid OpenAPI paths mapping you can merge into your schema builder.

Built-in OpenAPI endpoint:

- GET /openapi.json (public)

Optional OpenAPI settings:

.. code-block:: python

    NETS_CORE_OPENAPI_TITLE = "My API"
    NETS_CORE_OPENAPI_VERSION = "2.1.0"
    NETS_CORE_OPENAPI_DESCRIPTION = "Public API schema"
    NETS_CORE_OPENAPI_TAGS = ["auth", "users"]
    NETS_CORE_OPENAPI_MODULES = (
        "nets_core.google_auth",
        "nets_core.social_auth",
        "nets_core.views",
    )

Email Service
-------------

Entry point:

.. code-block:: python

    from nets_core.mail import send_email

Signature:

- subject
- email (str or list)
- template (path) or html
- context
- txt_template (optional)
- to_queued (default True)
- force (default False)
- attachments/files (optional)

Example:

.. code-block:: python

    sent, reason, description = send_email(
        subject="Verification",
        email=["user@example.com"],
        template="nets_core/email/verification_code.html",
        context={"button_link": {"label": "123456", "url": ""}},
        to_queued=False,
    )

Common reason codes:

- invalid_email
- email_domain_excluded
- empty_email
- template_not_found
- template_syntax_error
- template_or_html_required
- email_not_sent
- email_sent
- email_in_queue
- email_disabled
- invalid_attachment

Email behavior notes:

- If DEBUG=True and NETS_CORE_EMAIL_DEBUG_ENABLED=False, emails are skipped unless force=True.
- Excluded domains are controlled by NETS_CORE_EMAIL_EXCLUDE_DOMAINS.
- Footer is controlled by NETS_CORE_EMAIL_FOOTER, NETS_CORE_EMAIL_FOOTER_TEMPLATE, NETS_CORE_EMAIL_FOOTER_ENABLED.
- When attachments are present, queued mode is automatically downgraded to immediate send.

Wildcard exclusion examples:

.. code-block:: python

    NETS_CORE_EMAIL_EXCLUDE_DOMAINS = [
        "mailinator*",   # blocks mailinator.com, mailinator.org, etc.
        "temp-mail.org",
    ]

Push Notifications
------------------

Firebase setup:

.. code-block:: python

    FIREBASE_CONFIG = "/absolute/path/to/firebase-service-account.json"

Capabilities:

- Send single device message with data payload.
- Send user fan-out notifications to active devices.
- Persist notification delivery result/error in UserFirebaseNotification.

Security Utilities
------------------

SecureCache
^^^^^^^^^^^

``SecureCache`` is an HMAC-SHA256-backed cache wrapper that stores only
one-way digests — never the original key or value.  This makes it safe to use
for short-lived secrets such as password-reset tokens, email confirmation
codes, or any value where you need to verify correctness without the risk of
leaking the original from a compromised cache server.

How it works:

- **Keys** are hashed with HMAC-SHA256 before hitting the cache backend.
  A full cache dump cannot reveal what logical keys exist.
- **Values** are also stored as HMAC digests.  There is no way to decrypt
  them; you can only *validate* an incoming plaintext against the stored
  digest via ``validate()``.
- The HMAC secret is read from ``settings.NETS_CORE_SECURE_CACHE_KEY`` when
  set, otherwise falls back to Django's ``settings.SECRET_KEY``.

Recommended additional setting:

.. code-block:: python

    NETS_CORE_SECURE_CACHE_KEY = "a-long-random-string-different-from-SECRET_KEY"

Usage example:

.. code-block:: python

    from nets_core.security import SecureCache

    sc = SecureCache()

    # Store a one-time token for 5 minutes (300 seconds).
    sc.set("password_reset:user_42", raw_token, expiration=300)

    # Verify the token submitted by the user (constant-time comparison).
    if sc.validate("password_reset:user_42", submitted_token):
        sc.delete("password_reset:user_42")
        # proceed with the reset flow

Other security helpers:

- ``generate_tokens(user, oauth_app, expires=None)`` — create an
  ``AccessToken`` / ``RefreshToken`` pair directly without going through the
  OTP flow. Useful for service-to-service or testing scenarios.
- ``get_or_create_project_role(project, role_name)`` — ensure a
  project-scoped role exists.
- ``get_or_create_project_role_permission(project, role_name, codename)`` —
  ensure a permission is attached to a project role.
- ``add_user_to_role(user, project, role_name)`` — assign a user to a
  project-scoped role.

All authentication helpers use ``hmac.compare_digest`` for secret comparisons
to eliminate timing-attack surface.

Utility Helpers
---------------

get_upload_path
^^^^^^^^^^^^^^^

A ready-made ``upload_to`` callable for ``FileField`` / ``ImageField`` that
organises files by model name and upload date automatically:

.. code-block:: python

    from nets_core.utils import get_upload_path

    class Invoice(OwnedModel):
        attachment = models.FileField(upload_to=get_upload_path)
        cover      = models.ImageField(upload_to=get_upload_path, blank=True)

The resulting path follows the pattern::

    <model_name>/<YYYY>/<MM>/<DD>/<filename>

When the model instance has a ``project`` attribute the namespace is expanded::

    PSMDOC_PROJ_<project_id>/<model_name>/<YYYY>/<MM>/<DD>/<filename>

Filenames are sanitised (basename extraction) to prevent path-traversal
attacks from client-supplied names.

Other utility helpers:

- ``get_client_ip(request)`` — extract the originating IP respecting common
  reverse-proxy headers (``X-Forwarded-For``, ``X-Real-IP``, etc.).
- ``local_datetime(s, tz)`` — parse an ISO-8601 string and attach a timezone
  (defaults to ``settings.TIME_ZONE``).
- ``generate_int_uuid(size=None)`` — generate a numeric UUID suitable for
  surrogate keys.
- ``check_perm(user, action, project=None)`` — evaluate a permission codename
  for a user, with optional project-scoped resolution.  Supports the
  ``role:<name>`` shorthand for direct role-name matching.

Background Tasks
----------------

Available Celery tasks include:

- send_user_devices_notifications
- check_permissions
- get_google_avatar

For production, configure broker/backend and workers.

Channels Middleware
-------------------

AuthTokenMiddleware integrates OAuth2 Bearer token lookup into Django Channels
scope user resolution.

Recommended middleware stack usage:

.. code-block:: python

    from nets_core.middleware.auth_token import AuthTokenMiddlewareStack

    application = ProtocolTypeRouter({
        "websocket": AuthTokenMiddlewareStack(URLRouter(websocket_urlpatterns))
    })

Settings Reference (Exhaustive)
-------------------------------

Core auth and token settings:

- AUTHENTICATION_BACKENDS
- ACCESS_TOKEN_EXPIRE_SECONDS
- NETS_CORE_VERIFICATION_CODE_EXPIRE_SECONDS
- NETS_CORE_VERIFICATION_CODE_CACHE_KEY
- NETS_CORE_DEBUG_VERIFICATION_CODE

Verification code behavior:

- Default debug code is 123456 when DEBUG=True.
- You can override with NETS_CORE_DEBUG_VERIFICATION_CODE.

Social settings:

- GOOGLE_CLIENT_ID
- APPLE_CLIENT_ID

Email settings:

- DEFAULT_FROM_EMAIL
- NETS_CORE_EMAIL_DEBUG_ENABLED
- NETS_CORE_EMAIL_EXCLUDE_DOMAINS
- NETS_CORE_EMAIL_FOOTER_ENABLED
- NETS_CORE_EMAIL_FOOTER
- NETS_CORE_EMAIL_FOOTER_TEMPLATE

Project/permission settings:

- NETS_CORE_PROJECT_MODEL
- NETS_CORE_PROJECT_MEMBER_MODEL
- NETS_CORE_PROTECTED_FIELDS
- NETS_CORE_USER_PROHIBITED_FIELDS

Tester shortcuts:

- NETS_CORE_TESTERS_EMAILS
- NETS_CORE_TESTERS_VERIFICATION_CODE

Tester example:

.. code-block:: python

    NETS_CORE_TESTERS_EMAILS = [
        "google_tester*",
        "qa.user@yourcompany.com",
    ]
    NETS_CORE_TESTERS_VERIFICATION_CODE = "475638"

Notes:

- A value ending in * behaves as a prefix matcher.
- Keep tester values unique per environment.

UI template setting:

- NETS_CORE_DELETE_ACCOUNT_TEMPLATE

Delete account template example:

.. code-block:: python

    NETS_CORE_DELETE_ACCOUNT_TEMPLATE = "myapp/account_deletion_info.html"

User profile update guard:

- NETS_CORE_USER_PROHIBITED_FIELDS can extend blocked fields for /update/.
- Typical blocked fields include password, is_superuser, is_staff,
  user_permissions, and security metadata.

Infra settings commonly required:

- CACHES
- CELERY_BROKER_URL
- CELERY_RESULT_BACKEND
- CELERY_ACCEPT_CONTENT
- CELERY_RESULT_SERIALIZER
- CELERY_TASK_SERIALIZER
- CHANNEL_LAYERS
- ASGI_APPLICATION
- CORS_* settings according to your deployment policy

Operational Recommendations
---------------------------

- Keep OAuth2 Application records per client app and rotate client secrets.
- Set strict CORS/CSRF policies in production.
- Use Redis or Memcached for cache reliability.
- Monitor Celery queues and retry behavior.
- Configure NETS_CORE_EMAIL_FOOTER explicitly to avoid placeholder content.
- Use distinct tester settings per environment if enabled.

Security Notes
--------------

- Never trust raw provider tokens without server-side verification.
- Keep FIREBASE_CONFIG and OAuth credentials in secure secret storage.
- Treat NETS_CORE_TESTERS_* as high-risk settings and disable in production unless strictly needed.
- Set ``NETS_CORE_SECURE_CACHE_KEY`` to a secret distinct from ``SECRET_KEY``
  when using ``SecureCache`` in production.
- All secret comparisons in the authentication flow use ``hmac.compare_digest``
  to eliminate timing-attack surface.

Additional Documentation
------------------------

- docs/USAGE_GUIDE.rst
- CHANGELOG.md
- CONTRIBUTING.md
- SECURITY.md
- CODE_OF_CONDUCT.md

License
-------

BSD-3-Clause
