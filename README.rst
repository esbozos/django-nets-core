=========
NETS CORE
=========

And set of lazy API request handlers and common tasks. 
Just use it if you are really sure that you don't want to 
repeat common tasks in request from many sources.

REQUIREMENTS
____________
This package requires the following packages that will be installed automatically:

    Django
    pytz 
    python-dateutil
    shortuuid 
    django-oauth-toolkit 
    firebase-admin 
    django-cors-headers
    celery
    django-celery-beat
    djando-cors-headers
    django-memcached
    python-memcached
    pymemcache
    channels['daphne']

NOTES:
______
    - For celery to work, you need to set up a broker, for example, RabbitMQ or Redis. see https://docs.celeryq.dev/en/stable/getting-started/backends-and-brokers/index.html and set it in settings.py
    - Create a celery.py file in your project folder and set up the celery app see https://docs.celeryproject.org/en/stable/django/first-steps-with-django.html
    - For django-celery-beat to work, you need to set up a scheduler, for example, RabbitMQ or Redis. see https://docs.celeryproject.org/en/stable/userguide/periodic-tasks.html#starting-the-scheduler and set it in settings.py
    - For firebase to work, you need to set up a firebase project and download the credentials file and set it in settings.py as FIREBASE_CONFIG = os.path.join(BASE_DIR, 'firebase-credentials.json') see https://firebase.google.com/docs/admin/setup
    - For django-oauth-toolkit to work, you need to set up the authentication backend in settings.py as AUTHENTICATION_BACKENDS = ['oauth2_provider.backends.OAuth2Backend'] see https://django-oauth-toolkit.readthedocs.io/en/latest/rest-framework/getting_started.html#step-1-configure-your-authentication-backends
    - For django-cors-headers to work, you need to set up the middleware in settings.py as MIDDLEWARE = ['corsheaders.middleware.CorsMiddleware', 'django.middleware.common.CommonMiddleware'] see
    

COMMANDS:
_________

check if settings are set correctly
.. code-block:: bash
    
    ./manage.py nets-settings

create settings required for nets_core
.. code-block:: bash
    
    ./manage.py nets-settings --create 

force create settings required for nets_core and overwrite existing settings if any
.. code-block:: bash

    ./manage.py nets-settings --create --force 

create superuser
.. code-block:: bash

    ./manage.py createsuperuser




INSTALLATION
____________

.. code-block:: bash

    pip install django-nets-core

Add 'nets_core' to your INSTALLED_APPS setting like this:

.. code-block:: python

    INSTALLED_APPS = [
        ...
        'oauth2_provider', # required for authentication
        'nets_core',
    ]

Include the nets_core URLconf in your project urls.py like this:

.. code-block:: python

    path("", include("nets_core.auth_urls", namespace="auth")),


USAGE
_____


.. code-block:: python

    # this already include csrf_exempt for API requests
    from nets_core.decorators import request_handle
    from nets_core.params import RequestParam
    from django.http import JsonResponse

    from .models import MyModel

    @request_handle(
        MyModel, # model that you want to use if view requires it, this return 404 if not found and check ownership or permissions test in can_do param
        index_field='id' # field that will be used to get object from model, default is 'id',

        # params list that you want to get from request
        # this will be validated and converted to python types
        # if something is missing or wrong type, error will be raised
        # if public is True, this will be public in API and auth is not required
        # ensure you set you authentication methods in settings include OAuth2
        params=[
            RequestParam('name', str, optional=False),
        ],
        public=False, # default is False
        can_do=['action', 'module'], # this will be check permission for action and module, if this permission does not exist this will create it, add permissions to users in admin panel
        perm_required=False, # default is False, this will check if user has permission to do action or is owner of object, if set to TRUE only acces will be granted if can_do is passed

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

And set of lazy API request handlers and commong tasks. Just use it if you are really sure that you dont want to repeat common tasks in request from many sources.
settings VARS:

@request_handle
    include csrf_exempt

Cache is required for verification code:
check https://docs.djangoproject.com/en/4.1/topics/cache/ and pick your preference cache engine.

.. code-block:: python

    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.memcached.PyMemcacheCache',
            'LOCATION': '127.0.0.1:11211',
        }
    }

.. code-block:: python

    NS_VERIFICATION_CODE_EXPIRE_SECONDS = 15*60 # 900 seconds
    NS_EMAIL_FOOTER_ENABLED = True 
    NS_EMAIL_FOOTER = ''
    NS_EMAIL_DEBUG_ENABLED = False
    NS_EMAIL_FOOTER_TEMPLATE = None
    NS_EMAIL_EXCLUDE_DOMAINS = []
    NS_VERIFICATION_CODE_CACHE_KEY = 'NC_T'

.. code-block:: python

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
    # set this in your settings.py to exclude fields from user model to be updated by auth.urls
    NETS_CORE_USER_PROHIBITED_FIELDS = prohibited_fields 

.. code-block:: python

    # if you want to use auth.urls
    # auth url accept device_uuid with email, core, client_id and client_secret to get access token
    path("", include("nets_core.auth_urls", namespace="auth")),

.. code-block:: python

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


DJANGO SETTINGS
================

.. code-block:: python

    DEFAULT_FROM_EMAIL is used for emails

    CORS REQUEST AND POST require
    CSRF_COOKIE_SAMESITE = 'None'
    CSRF_COOKIE_SECURE = True

.. code-block:: python

    # firebase credentials
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



Authentication is made with:
____________________________
    django-oauth-toolkit
    django-cors-headers



Authentication
______________

    from nets_core.security import authenticate
    authenticate(user, code, client_id, client_secret)

Just to be lazy.
