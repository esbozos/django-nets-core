Django NETS CORE
================

Production-oriented toolkit for Django APIs: request validation, OTP login, OAuth2 token issuance, social login, role/permission management, email delivery, and push notifications.

Status
------

This package is actively evolving. Current release metadata is managed in setup.cfg.

Why NETS CORE
-------------

NETS CORE helps teams ship API backends faster by reducing repeated boilerplate in:

- Request parsing and strict parameter validation.
- Authentication flows (OTP + OAuth2 token generation).
- Social sign-in onboarding.
- Role and permission assignment (global and project-scoped).
- Email and push notification plumbing.
- JSON serialization patterns for model responses.

Core Capabilities
-----------------

Authentication and Sessions
^^^^^^^^^^^^^^^^^^^^^^^^^^^

- OTP flow with verification code model, expiration, and cache-backed checks.
- OAuth2 access and refresh token generation using django-oauth-toolkit.
- Social login endpoints for Google, Apple, Facebook, Microsoft, and GitHub.
- Legacy Google endpoint preserved for backwards compatibility.

Validation and Endpoint Ergonomics
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- request_handler decorator for auth checks, permission checks, object loading, and param parsing.
- RequestParam type conversion for common API types (str, int, bool, float, date, datetime, dict, list, email, file).
- Unified JSON success/error response helpers.

Data and Access Model
^^^^^^^^^^^^^^^^^^^^^

- Abstract base models with automatic created/updated timestamps.
- updated_fields tracking for model change history.
- Built-in Permission, Role, RolePermission, and UserRole models.
- Optional project-scoped role/permission resolution.

Communications
^^^^^^^^^^^^^^

- Email delivery with template rendering, queue support, domain filtering, optional attachments, and debug controls.
- Firebase Cloud Messaging integration for device-targeted notifications.

Developer Tooling
^^^^^^^^^^^^^^^^^

- Management command to inspect/bootstrap expected settings: nets-settings.
- Django admin registrations for core auth/email/permission entities.

Installation
------------

.. code-block:: bash

    pip install django-nets-core

Quick Start
-----------

1) Add required apps:

.. code-block:: python

    INSTALLED_APPS = [
        # ...
        "oauth2_provider",
        "nets_core",
    ]

2) Add auth URLs:

.. code-block:: python

    from django.urls import include, path

    urlpatterns = [
        path("", include("nets_core.auth_urls", namespace="auth")),
    ]

3) Ensure authentication backend compatibility:

.. code-block:: python

    AUTHENTICATION_BACKENDS = [
        "oauth2_provider.backends.OAuth2Backend",
        "django.contrib.auth.backends.ModelBackend",
    ]

4) Run migrations:

.. code-block:: bash

    python manage.py migrate

5) Verify settings scaffold:

.. code-block:: bash

    python manage.py nets-settings

Authentication API
------------------

Base Auth Endpoints
^^^^^^^^^^^^^^^^^^^

- POST /login/ -> creates/gets user and issues verification code.
- POST /authenticate/ -> validates code and returns OAuth2 tokens.
- POST /logout/ -> revokes session/token.
- GET/POST /getProfile/ -> returns user profile fields.
- POST /update/ -> updates user model fields (excluding protected ones).

Social Login Endpoints
^^^^^^^^^^^^^^^^^^^^^^

- POST /loginWithGoogle/ (legacy endpoint from google_auth module).
- POST /loginWithGoogleSocial/ (new unified social flow).
- POST /loginWithApple/
- POST /loginWithFacebook/
- POST /loginWithMicrosoft/
- POST /loginWithGithub/

Social Endpoint Payload
^^^^^^^^^^^^^^^^^^^^^^^

All social endpoints receive:

.. code-block:: json

    {
      "token": "provider_access_or_id_token",
      "client_id": "oauth_application_client_id",
      "client_secret": "oauth_application_client_secret"
    }

Social Endpoint Response
^^^^^^^^^^^^^^^^^^^^^^^^

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

Social Provider Configuration
-----------------------------

Required provider settings depend on endpoint usage:

- GOOGLE_CLIENT_ID for Google token validation.
- APPLE_CLIENT_ID for Apple audience validation.

Facebook, Microsoft, and GitHub currently validate by calling provider APIs with the received token.

Important: OAuth2 application credentials (client_id/client_secret) are always validated against django-oauth-toolkit Application records before issuing NETS CORE tokens.

Legacy Compatibility Note
-------------------------

The original Google implementation remains available at /loginWithGoogle/. New projects should prefer /loginWithGoogleSocial/ to keep all providers under one shared flow.

Using request_handler
---------------------

Example:

.. code-block:: python

    from django.http import JsonResponse
    from nets_core.decorators import request_handler
    from nets_core.params import RequestParam

    @request_handler(
        params=[
            RequestParam("name", str),
            RequestParam("age", int, optional=True, default=18),
        ],
        public=False,
        can_do="myapp.can_change_profile",
        perm_required=False,
    )
    def my_view(request):
        return JsonResponse({"ok": True, "name": request.params.name})

Behavior summary:

- Parses params from JSON body, form body, querystring, and files.
- Casts values to declared types.
- Returns 400 with standardized error payload on invalid input.
- Optionally checks permissions/roles and object ownership.

RequestParam Supported Types
----------------------------

- Python types: str, int, bool, float, dict, list.
- Named types: date, datetime, email, file.
- Custom validators through validate callable.

Core Models
-----------

- NetsCoreBaseModel: created/updated/updated_fields + to_json.
- OwnedModel: base model + user ownership.
- VerificationCode: OTP lifecycle.
- UserDevice: user device tracking and firebase token storage.
- Permission, Role, RolePermission, UserRole: authorization graph.
- EmailTemplate, EmailNotification, CustomEmail: email composition/delivery metadata.
- UserFirebaseNotification: push delivery tracking.

Email Integration
-----------------

Entry point:

.. code-block:: python

    from nets_core.mail import send_email

Example:

.. code-block:: python

    sent, reason, description = send_email(
        subject="Welcome",
        email=["user@example.com"],
        template="myapp/email/welcome.html",
        context={"name": "Ada"},
        txt_template="myapp/email/welcome.txt",
        to_queued=False,
    )

Highlights:

- Domain exclusion via NETS_CORE_EMAIL_EXCLUDE_DOMAINS.
- Footer branding via NETS_CORE_EMAIL_FOOTER / NETS_CORE_EMAIL_FOOTER_TEMPLATE.
- Debug guard via NETS_CORE_EMAIL_DEBUG_ENABLED.
- Attachment normalization and validation.

Push Notifications
------------------

Firebase integration is available through nets_core.firebase_messages.

Minimal requirement:

.. code-block:: python

    FIREBASE_CONFIG = "/absolute/path/to/firebase-service-account.json"

Then send notifications to active user devices through internal helpers/tasks.

Selected Settings Reference
---------------------------

Auth and Verification
^^^^^^^^^^^^^^^^^^^^^

- NETS_CORE_VERIFICATION_CODE_EXPIRE_SECONDS
- NETS_CORE_DEBUG_VERIFICATION_CODE
- NETS_CORE_VERIFICATION_CODE_CACHE_KEY
- ACCESS_TOKEN_EXPIRE_SECONDS

Email
^^^^^

- NETS_CORE_EMAIL_DEBUG_ENABLED
- NETS_CORE_EMAIL_EXCLUDE_DOMAINS
- NETS_CORE_EMAIL_FOOTER_ENABLED
- NETS_CORE_EMAIL_FOOTER
- NETS_CORE_EMAIL_FOOTER_TEMPLATE

Project and Permissions
^^^^^^^^^^^^^^^^^^^^^^^

- NETS_CORE_PROJECT_MODEL
- NETS_CORE_PROJECT_MEMBER_MODEL
- NETS_CORE_PROTECTED_FIELDS
- NETS_CORE_USER_PROHIBITED_FIELDS

Infrastructure
^^^^^^^^^^^^^^

- CACHES
- CELERY_BROKER_URL / CELERY_RESULT_BACKEND
- CHANNEL_LAYERS
- AUTHENTICATION_BACKENDS

Operational Notes
-----------------

- Configure cache before enabling OTP in production.
- Configure Celery/Redis if you rely on queued jobs.
- Ensure oauth2_provider Application records exist for your client apps.
- Set NETS_CORE_EMAIL_FOOTER explicitly in production to avoid default placeholder footer.

Management Command
------------------

Inspect and optionally scaffold baseline settings:

.. code-block:: bash

    python manage.py nets-settings
    python manage.py nets-settings --create
    python manage.py nets-settings --create --force

Additional Documentation
------------------------

For architecture and implementation patterns, see:

- docs/USAGE_GUIDE.rst

Contributing
------------

- Read CONTRIBUTING.md
- Read SECURITY.md for vulnerability reporting
- Follow CODE_OF_CONDUCT.md

License
-------

BSD-3-Clause
