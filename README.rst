=========
NETS CORE
=========

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

DJANGO SETTINGS
DEFAULT_FROM_EMAIL is used for emails

CORS REQUEST AND POST require

    CSRF_COOKIE_SAMESITE = 'None'
    CSRF_COOKIE_SECURE = True

Authentication is made with:
    django-oauth-toolkit
    django-cors-headers

    from nets_core.security import authenticate
    authenticate(user, code, client_id, client_secret)

Just to be lazy.
