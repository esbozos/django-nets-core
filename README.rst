TODO: DOCUMENTATION PENDING
===========================

- [ ] Add documentation in PSMDOC format
- [ ] Add examples of send email, PUSH NOTIFICATIONS, SMS, etc
- [ ] Add examples of create roles and permissions in multi project support
- [ ] Add examples of request_handler usage to validate permissions, ownership, etc

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
    django-cors-headers
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
        # if ProjectMemberModel has role field can_do can be use with role names
        # can_do='role:admin' will check if user has role admin in project or is owner of object
        can_do='myapp.can_delete_object', # this will be check permission to do action, if not passed, only owner of object can do action, if permission does not exists will be created
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

    from nets_core.models import OwnedModel, NetsCoreBaseModel
    # use of OwnedModel is optional, but recommended to include user, created and updated fields, 
    # if not used, include user, created and updated fields in your model
    class MyProjectModel(OwnedModel):
        name = models.CharField(max_length=255)
        enabled = models.BooleanField(default=True)
        description = models.TextField(blank=True, null=True)

        PROTECTED_FIELDS = ['user']
        JSON_DATA_FIELDS=['name', 'description', 'enabled', 'created', 'updated' ] # OPTIONAL, but recommended is extends OwnedModel or NetsCoreBaseModel , fields to include in json data if to_json is called witout fields parameter

        def __str__(self):
            return self.name

    MEMBER_ROLES = [
        ('superuser', 'Superuser'),
        ('member', 'Member'),
        ('admin', 'Admin'),
        ('viewer', 'Viewer')
    ]
    class MyProjectMemberModel(OwnedModel):
        project = models.ForeignKey(MyProjectModel, on_delete=models.CASCADE)        
        is_superuser = models.BooleanField(default=False)
        enabled = models.BooleanField(default=True)    
        role = models.CharField(max_length=255, choices=MEMBER_ROLES, default='member')  # OPTIONAL but recommended to use in access control by roles see can_do param in request_handler
        JSON_DATA_FIELDS = ['id', 'is_superuser', 'role', 'user'] # User is a ForeignKey to user model, foreign models to include in json data should extend OwnedModel or NetsCoreBaseModel and include JSON_DATA_FIELDS is required

        PROTECTED_FIELDS = ['is_superuser', 'project']
        

        def __str__(self):
            return f'{self.user} - {self.project}'


        # example of custom method to convert member to json
        # each model that extends OwnedModel or NetsCoreBaseModel
        # has a to_json method that can be used to convert the model to json    
        def member_to_json(self):
            """
            Convert the member object to a JSON representation.

            :return: A dictionary representing the member object in JSON format.
            """
            return {
                'id': self.id,
                'project_id': self.project.id,
                'user_id': self.user.id,
                'role': self.role,
                'user': self.user.to_json(fields=('id', 'first_name', 'last_name')),
            }

Setting  is_superuser to True will give user superuser permissions over project, OwnedModel is Abstract model that include user, created and updated fields

.. warning::
   The `NetsCoreBaseModel` is an abstract model that includes `created` and `updated` fields. It implements a `to_json` method that allows the model to be serialized to JSON. This method accepts fields as a tuple to include or `"__all__"` to include all fields. This is a stored function in the database for fast access to JSON data.

   `PROTECTED_FIELDS` is a list of fields that will not be exposed, even if the request includes these fields. If `PROTECTED_FIELDS` is not set, all fields that contain any `NETS_CORE_GLOBAL_PROTECTED_FIELDS` will be removed from the response. For example, fields such as `'old_password'`, `'password'`, `'origin_ip'`, `'ip'` will be removed from the response if not set in `PROTECTED_FIELDS` in your model class. You can set `NETS_CORE_GLOBAL_PROTECTED_FIELDS` in your `settings.py` to replace the default fields to be protected.

   `NetsCoreBaseModel` includes `updated_fields`, which is a `JSONField` that will store changes in the model. This field will be updated by `nets_core` when the model is updated. This is useful for tracking changes in the model. Do not make changes to this field, as it will be updated by `nets_core`.

   `OwnerModel` extends `NetsCoreBaseModel` and includes a `user` field. This is useful for tracking the ownership of the model and will be used to check if a user is the owner of the model.

    TODO: include examples of use to serialize model to json based on fields required per view or endpoint. Inspired in Facebook GraphQL


set NETS_CORE_GLOBAL_PROTECTED_FIELDS
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    NETS_CORE_PROTECTED_FIELDS = [
        'password',
        'is_active',
        'enabled',
        'staff',
        'superuser',
        'verified',
        'deleted',
        'token',
        'auth',
        'perms',
        'groups',
        'ip',
        'email',
        'doc',
        'permissions',
        'date_joined',
        'last_login',
        'verified',
        'updated_fields'
    ] # default fields to be protected


Set verification code expire time
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    NETS_CORE_VERIFICATION_CODE_EXPIRE_SECONDS = 15*60 # 900 seconds

Set email footer
^^^^^^^^^^^^^^^^

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
^^^^^^^^^^^^^^^^^^^^

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
^^^^^^^^^^^^^^^^^^^^^

.. warning::
    This will be deprecated in future versions, use PROTECTED_FIELDS in your model class to exclude fields from being updated by auth.urls

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
this could end with \* to allow all emails that start with the string before the \*, for production use a strong string and different for each project 
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
============
    Django
    pytz
    python-dateutil
    shortuuid
    django-oauth-toolkit
    firebase-admin
    django-cors-headers



Authentication is made with:
============================
    django-oauth-toolkit
    django-cors-headers



Authentication
==============

    from nets_core.security import authenticate
    authenticate(user, code, client_id, client_secret)

Just to be lazy.
