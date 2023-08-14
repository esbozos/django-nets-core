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


NS_VERIFICATION_CODE_EXPIRE_SECONDS = 15*60 # 900 seconds
NS_EMAIL_FOOTER_ENABLED = True 
NS_EMAIL_FOOTER = ''
NS_EMAIL_DEBUG_ENABLED = False
NS_EMAIL_FOOTER_TEMPLATE = None
NS_EMAIL_EXCLUDE_DOMAINS = []
NS_VERIFICATION_CODE_CACHE_KEY = 'NC_T'

DJANGO SETTINGS
DEFAULT_FROM_EMAIL is used for emails

CORS REQUEST AND POST require

    CSRF_COOKIE_SAMESITE = 'None'
    CSRF_COOKIE_SECURE = True

Dependencies
____________

Authentication is made with:
    django-oauth-toolkit
    django-cors-headers

    from nets_core.security import authenticate
    authenticate(user, code, client_id, client_secret)

Just to be lazy.
