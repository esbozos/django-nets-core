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
    from nets_core.decorators import request_handler
    from nets_core.params import RequestParam
    from django.http import JsonResponse

    from .models import MyModel

    @request_handler(
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

NETS_CORE SETTINGS
__________________

Enabled multi project support
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    NETS_CORE_PROJECT_MODEL = 'myapp.MyProjectModel'
    NETS_CORE_PROJECT_MEMBER_MODEL = 'myapp.MyProjectMemberModel'

Note that both models should be defined in your settings file. Both require def __str__(self): to be defined.
If enabled roles and permissions will be check over project and membership enabled	
example of models:

.. code-block:: python

    class MyProjectModel(models.Model):
        name = models.CharField(max_length=255)
        enabled = models.BooleanField(default=True)
        description = models.TextField(blank=True, null=True)
        created_at = models.DateTimeField(auto_now_add=True)
        updated_at = models.DateTimeField(auto_now=True)

        def __str__(self):
            return self.name

    class MyProjectMemberModel(models.Model):
        project = models.ForeignKey(MyProjectModel, on_delete=models.CASCADE)
        user = models.ForeignKey(User, on_delete=models.CASCADE) # User from django.contrib.auth.models or your custom user model
        enabled = models.BooleanField(default=True)
        created_at = models.DateTimeField(auto_now_add=True)
        updated_at = models.DateTimeField(auto_now=True)

        def __str__(self):
            return f'{self.user} - {self.project}'


Set verification code expire time
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    NETS_CORE_VERIFICATION_CODE_EXPIRE_SECONDS = 15*60 # 900 seconds

Set email footer
^^^^^^^^^^^^^^^

.. code-block:: python

    NETS_CORE_EMAIL_FOOTER_ENABLED = True 
    NETS_CORE_EMAIL_FOOTER = '<p>Thank you for using our service </p>' # html email footer
    NETS_CORE_EMAIL_FOOTER_TEMPLATE = 'myapp/email_foote.html' # template to use for email footer


.. warning::
    
    If NETS_CORE_EMAIL_FOOTER_TEMPLATE is set, NETS_CORE_EMAIL_FOOTER will be ignored


Set email debug
^^^^^^^^^^^^^^^

Enable sent emails while settings.DEBUG is True, default to False. Enable if you want sent emails in development
.. code-block:: python

    NETS_CORE_EMAIL_DEBUG_ENABLED = True


Set excluded domains
^^^^^^^^^^^^^^^^^^^

Sometimes you want to exclude some domains from sent emails to avoid spamming, like temporary emails or testing domains
like service providers as mailinator.com, temp-mail.org, guerillamail.com, emailondeck.com, ironmail.com, cloakmail.com, 10minutemail.com, 33mail.com, maildrop.cc, etc.

.. code-block:: python

    NETS_CORE_EMAIL_EXCLUDE_DOMAINS = ['mailinator.com', 'temp-mail.org', 'guerillamail.com', 'emailondeck.com', 'ironmail.com', 'cloakmail.com', '10minutemail.com', '33mail.com', 'maildrop.cc']

This will avoid to send emails to these domains: example user request access with me@guerillamail.com will not receive any email


Set verification code cache key
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Set cache key to store verification code, default is 'NC_T'
.. code-block:: python

    NETS_CORE_VERIFICATION_CODE_CACHE_KEY = 'NC_T'

Set prohibited fields
^^^^^^^^^^^^^^^^^^^^

nets_core.auth_urls provide endpoints to update user model fields, you can exclude some fields from being updated by auth.urls

Set fields that should not be updated by auth.urls
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


Include nets_core.auth_urls
^^^^^^^^^^^^^^^^^^^^^^^^^^^

To enabled authentication provided by nets_core include auth.urls in your project urls.py

.. code-block:: python
    
    from django.urls import path, include

    urlpatterns = [
        ...
        path("", include("nets_core.auth_urls", namespace="auth")),
        ...
    ]


Enabled testers for tests or third party verifications
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Enabling testers will allow test autentication without receiving email verification code, for this to work
you need to set the following settings

.. code-block:: python

    NETS_CORE_TESTERS_EMAILS = ['google_testers234*', 'tester1@myappdomain.com']
    NETS_CORE_TESTERS_VERIFICATION_CODE = '475638'

NETS_CORE_TESTERS_EMAILS is a list of emails that will be allowed to authenticate without receiving email verification code
this could end with * to allow all emails that start with the string before the *, for production use a strong string and different for each project 
and environment, to avoid unauthorized access

NETS_CORE_TESTERS_VERIFICATION_CODE is the verification code that will be used to authenticate testers

.. warning::

    Use a unique and strong string emails and verification code for each project and environment to avoid unauthorized access


Customize account deletion template
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To customize the account deletion email template, create a template in your project templates folder
and set the path in settings.py

.. code-block:: python

    NETS_CORE_DELETE_ACCOUNT_TEMPLATE = 'myapp/account_deletion.html'

This will  include and info template in account deletion view.


.. warning::

    If NETS_CORE_DELETE_ACCOUNT_TEMPLATE is not set not info template will be included in account deletion view




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
