=========
NETS CORE
=========

And set of lazy API request handlers and common tasks. 
Just use it if you are really sure that you don't want to 
repeat common tasks in request from many sources.


.. code-block:: python

    # this already include csrf_exempt for API requests
    from nets_core.decorators import request_handle
    from nets_core.params import RequestParam
    from django.http import JsonResponse

    @request_handle(

        # params list that you want to get from request
        # this will be validated and converted to python types
        # if something is missing or wrong type, error will be raised
        # if public is True, this will be public in API and auth is not required
        # ensure you set you authentication methods in settings include OAuth2
        params=[
            RequestParam('name', str, optional=False),
        ],
        public=False, # default is False
    )
    def my_view(request):
        # do something
        return JsonResponse({'ok': True})
        

Cache is required for verification code:
check https://docs.djangoproject.com/en/4.1/topics/cache/ and pick your preference 
cache engine and set it in settings.py.

.. code-block:: python

    CACHES = {
        'default': {
        'BACKEND': 'django.core.cache.backends.memcached.PyMemcacheCache',
        'LOCATION': '127.0.0.1:11211'
        }
    }


settings VARS:
______________

=======
And set of lazy API request handlers and commong tasks. Just use it if you are really sure that you dont want to repeat common tasks in request from many sources.
settings VARS:

@request_handle
    include csrf_exempt

Cache is required for verification code:
check https://docs.djangoproject.com/en/4.1/topics/cache/ and pick your preference cache engine.
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.PyMemcacheCache',
        'LOCATION': '127.0.0.1:11211',
    }
}

NS_VERIFICATION_CODE_EXPIRE_SECONDS = 15*60 # 900 seconds
NS_EMAIL_FOOTER_ENABLED = True 
NS_EMAIL_FOOTER = ''
NS_EMAIL_DEBUG_ENABLED = False
NS_EMAIL_FOOTER_TEMPLATE = None
NS_EMAIL_EXCLUDE_DOMAINS = []
NS_VERIFICATION_CODE_CACHE_KEY = 'NC_T'

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

.. code-block:: python

    # if you want to use auth.urls
 path("", include("nets_core.auth_urls", namespace="auth")),

.. set this in your settings.py to exclude fields from user model to be updated by auth.urls
NETS_CORE_USER_PROHIBITED_FIELDS = prohibited_fields 
try:
    if settings.NETS_CORE_USER_PROHIBITED_FIELDS:
        prohibited_fields += settings.NETS_CORE_USER_PROHIBITED_FIELDS
except:
    pass

.. code-block:: python
    # login url accept device to link verification code to device
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
    valid_device_fields is use to update or create device
    if uuid is provided, device will be updated, otherwise created
    if invalid uuid is provided, error will be raised

    # auth url accept device_uuid with email, core, client_id and client_secret to get access token


=======
DJANGO SETTINGS
DEFAULT_FROM_EMAIL is used for emails

CORS REQUEST AND POST require

    CSRF_COOKIE_SAMESITE = 'None'
    CSRF_COOKIE_SECURE = True


FIREBASE_CONFIG = os.path.join(BASE_DIR, 'firebase-credentials.json')
Dependencies
____________
    Django
    pytz 
    python-dateutil
    shortuuid 
    django-oauth-toolkit 
    firebase-admin 
    django-cors-headers


=======
Authentication is made with:
    django-oauth-toolkit
    django-cors-headers



=======
    from nets_core.security import authenticate
    authenticate(user, code, client_id, client_secret)

Just to be lazy.

=======
