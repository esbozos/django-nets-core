from datetime import datetime
from pathlib import Path, PosixPath
from django.core.management.base import BaseCommand
from django.conf import settings
import os
import json
import sys
import importlib
import re

class Command(BaseCommand):
    # use stdout and styles to print messages
    help="""
        This command will check if required settings are present in the settings.py file.
        and check if addtional files are present and configured correctly.
        
        if --create flag is passed, it will create the missing files and add the required settings.
        
        for settings.py file, it will check for the following settings:
        oauth2_provider, django_celery_beat, corsheaders,  nets_core in INSTALLED_APPS
        nets-core.auth_urls in ROOT_URLCONF
        corsheaders.middleware.CorsMiddleware in MIDDLEWARE
        oauth2_provider.middleware.OAuth2TokenMiddleware in MIDDLEWARE        
        
        site variables:
        SITE_DOMAIN = ''
        SITE_NAME = ''
        SITE_LOGO = ''
        SITE_LOGO_WHITE = ''
        SITE_LOGO_BLACK = ''
        SITE_DESCRIPTION = ''
        
        celery settings:
            this should be present in settings.py if --create flag is passed default settings will be added using redis as broker and result backend. 
            Please make sure redis is installed and running. and /0 is the default database. if you have others projects using redis, please change the database number to avoid conflicts.
            CELERY_BROKER_URL = 'redis://localhost:6379/0'
            CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
            CELERY_ACCEPT_CONTENT = ['application/json']
            CELERY_RESULT_SERIALIZER = 'json'
            CELERY_TIMEZONE = TIME_ZONE
            CELERY_TASK_SERIALIZER = 'json'
        
        will add read of the environment variable DJANGO_ENV and add it to the settings.py file.
        ENV = os.getenv('DJANGO_ENV')
        will add check for settings_[ENV].py and import it if it exists.
        if ENV:
            try:
                from .settings_{} import *
            except ImportError:
                pass
        
        
        celery
        Add required settings for nets-core to settings.py 
        create a celery.py file in the project root directory.
    """
    
    REQUIRE_SETTINGS = [
        'INSTALLED_APPS',
        'ROOT_URLCONF',
        'MIDDLEWARE',
        'SITE_DOMAIN',
        'SITE_NAME',
        'CELERY_BROKER_URL',
        'CELERY_RESULT_BACKEND',
        'CELERY_ACCEPT_CONTENT',
        'CELERY_RESULT_SERIALIZER',
        'CELERY_TIMEZONE',
        'CELERY_TASK_SERIALIZER',
        'ENV',
        'CACHES',
        'ASGI_APPLICATION',
        'CHANNEL_LAYERS',
        'SESSION_ENGINE',
        'SESSION_COOKIE_NAME',
        'SESSION_COOKIE_AGE',
        'SESSION_COOKIE_SECURE',
        'SESSION_COOKIE_SAMESITE',
        'CACHE_MIDDLEWARE_KEY_PREFIX',
        'AUTHENTICATION_BACKENDS',
    ]
    
    def add_arguments(self, parser):
        parser.add_argument('--create', action='store_true', help='Create missing files and add required settings to settings.py')
        parser.add_argument('--force', action='store_true', help='Force create missing files and add required settings to settings.py')
        parser.add_argument('--site-domain', type=str, help='Site domain')
        parser.add_argument('--site-name', type=str, help='Site name')
        
    def handle(self, *args, **options):
        from django.conf import settings
        base_dir = settings.BASE_DIR
        
        create = options.get('create')
        force = options.get('force')
        site_domain = options.get('site_domain')
        site_name = options.get('site_name')
        
        
        
        if create:            
            if not site_domain:
                if hasattr(settings, 'SITE_DOMAIN'):
                    site_domain = settings.SITE_DOMAIN
                else:
                    
                    site_domain = input('Enter the site domain: ')
        
            if not site_name:
                if hasattr(settings, 'SITE_NAME'):
                    site_name = settings.SITE_NAME
                else:
                    site_name = input('Enter the site name: ')
        
            self.create_files(site_domain, site_name, force=force)
        
        else:
            self.check_settings(site_domain, site_name)
            
            
    def check_settings(self, site_domain, site_name):
        # check if the required settings are present in the settings.py file.
        # and check if addtional files are present and configured correctly.
        from django.conf import settings
        base_dir = settings.BASE_DIR
        
        
        
        # check for installed apps
        
        try:
            installed_apps = settings.INSTALLED_APPS
            if 'oauth2_provider' not in installed_apps:
                self.stdout.write(self.style.ERROR('oauth2_provider not found in INSTALLED_APPS in settings.py file.'))            
            
            
            if 'django_celery_beat' not in installed_apps:
                self.stdout.write(self.style.ERROR('django_celery_beat not found in INSTALLED_APPS in settings.py file.'))            
            
            
            if 'corsheaders' not in installed_apps:
                self.stdout.write(self.style.ERROR('corsheaders not found in INSTALLED_APPS in settings.py file.'))
            
            if 'nets_core' not in installed_apps:
                self.stdout.write(self.style.ERROR('nets_core not found in INSTALLED_APPS in settings.py file.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR('INSTALLED_APPS not found in settings.py file.'))
            pass
        
        
        # check for ROOT_URLCONF
                       
        if not hasattr(settings, 'ROOT_URLCONF'):
            self.stdout.write(self.style.ERROR('ROOT_URLCONF not found in settings.py file.'))
            pass
        # check for MIDDLEWARE
        
        try:
            middleware = settings.MIDDLEWARE
            if 'corsheaders.middleware.CorsMiddleware' not in middleware:
                self.stdout.write(self.style.ERROR('corsheaders.middleware.CorsMiddleware not found in MIDDLEWARE in settings.py file.'))
            
            if 'oauth2_provider.middleware.OAuth2TokenMiddleware' not in middleware:
                self.stdout.write(self.style.ERROR('oauth2_provider.middleware.OAuth2TokenMiddleware not found in MIDDLEWARE in settings.py file.'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR('MIDDLEWARE not found in settings.py file.'))
            pass
        
        try:
            site_domain = settings.SITE_DOMAIN
            site_name = settings.SITE_NAME
        except Exception as e:
            self.stdout.write(self.style.ERROR('SITE_DOMAIN or SITE_NAME not found in settings.py file.'))
            pass
        
        try:
            celery_broker_url = settings.CELERY_BROKER_URL
            celery_result_backend = settings.CELERY_RESULT_BACKEND
            celery_accept_content = settings.CELERY_ACCEPT_CONTENT
            celery_result_serializer = settings.CELERY_RESULT_SERIALIZER
            celery_timezone = settings.CELERY_TIMEZONE
            celery_task_serializer = settings.CELERY_TASK_SERIALIZER
        except Exception as e:
            self.stdout.write(self.style.ERROR('Celery settings not found in settings.py file.'))
            pass
        
        try:
            env = settings.ENV
        except Exception as e:
            self.stdout.write(self.style.NOTICE('ENV not found in settings.py file. This is optional.'))
            pass
            
        
        try:
            asgi_application = settings.ASGI_APPLICATION
        except Exception as e:
            self.stdout.write(self.style.ERROR('ASGI_APPLICATION not found in settings.py file.'))
            pass
        
        try:
            channel_layers = settings.CHANNEL_LAYERS
        except Exception as e:
            self.stdout.write(self.style.ERROR('CHANNEL_LAYERS not found in settings.py file.'))
            pass
        
        try:
            caches = settings.CACHES
        except Exception as e:
            self.stdout.write(self.style.ERROR('CACHES not found in settings.py file.'))
            pass
        
        try:
            session_engine = settings.SESSION_ENGINE
            session_cookie_name = settings.SESSION_COOKIE_NAME
            session_cookie_age = settings.SESSION_COOKIE_AGE
            session_cookie_secure = settings.SESSION_COOKIE_SECURE
            session_cookie_samesite = settings.SESSION_COOKIE_SAMESITE
            cache_middleware_key_prefix = settings.CACHE_MIDDLEWARE_KEY_PREFIX
            authentication_backends = settings.AUTHENTICATION_BACKENDS
        except Exception as e:
            self.stdout.write(self.style.ERROR('Session settings not found in settings.py file.'))
            pass
        
        
        
    def create_files(self, site_domain, site_name, force=False):
        time = datetime.now().strftime('%Y%m%d%H%M%S')
        # create the missing files and add the required settings.
        from django.conf import settings as django_settings
        base_dir = django_settings.BASE_DIR
        
        manage_py = os.path.join(base_dir, 'manage.py')
        if not os.path.exists(manage_py):
            self.stdout.write(self.style.ERROR('manage.py not found.'))
            sys.exit(1)
        
        # get  os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nets_core.settings') from manage.py
        try:
            with open(manage_py, 'r') as f:
                manage_py_content = f.read()
                settings_module_env = re.findall(r"os.environ.setdefault\('DJANGO_SETTINGS_MODULE', '(.*)'\)", manage_py_content)
                self.stdout.write(settings_module_env[0])
                project_name = settings_module_env[0].split('.')[0]
                if not os.path.exists(os.path.join(base_dir, f'{project_name}/settings.py')):
                    self.stdout.write(self.style.ERROR(f'{project_name}/settings.py not found.'))
                    sys.exit(1)
                else:
                    settings = importlib.import_module(f'{project_name}.settings')
                    
                

        except Exception as e:
            self.stdout.write(self.style.ERROR(e))
            self.stdout.write(self.style.ERROR('Error reading manage.py file. Please run the command from the project root directory.'))
            sys.exit(1)
            
        # check for installed apps
        if not 'daphne' in settings.INSTALLED_APPS:
            self.stdout.write(self.style.NOTICE('Adding daphne to INSTALLED_APPS in settings.py file.'))
            settings.INSTALLED_APPS = ['daphne'] + settings.INSTALLED_APPS
            
        if 'oauth2_provider' not in settings.INSTALLED_APPS:
            self.stdout.write(self.style.NOTICE('Adding oauth2_provider to INSTALLED_APPS in settings.py file.'))
            settings.INSTALLED_APPS.append('oauth2_provider')
        
        if 'django_celery_beat' not in settings.INSTALLED_APPS:
            self.stdout.write(self.style.NOTICE('Adding django_celery_beat to INSTALLED_APPS in settings.py file.'))
            settings.INSTALLED_APPS.append('django_celery_beat')
            
        if 'corsheaders' not in settings.INSTALLED_APPS:
            self.stdout.write(self.style.NOTICE('Adding corsheaders to INSTALLED_APPS in settings.py file.'))
            settings.INSTALLED_APPS.append('corsheaders')
            
        if 'nets_core' not in settings.INSTALLED_APPS:
            self.stdout.write(self.style.NOTICE('Adding nets_core to INSTALLED_APPS in settings.py file.'))
            settings.INSTALLED_APPS.append('nets_core')
            
        # check for ROOT_URLCONF
        if not hasattr(settings, 'ROOT_URLCONF'):
            self.stdout.write(self.style.NOTICE('Adding ROOT_URLCONF to settings.py file.'))
            settings.ROOT_URLCONF = f'{project_name}.urls'
            
        # check for MIDDLEWARE
        if 'corsheaders.middleware.CorsMiddleware' not in settings.MIDDLEWARE:
            self.stdout.write(self.style.NOTICE('Adding corsheaders.middleware.CorsMiddleware to MIDDLEWARE in settings.py file.'))
            settings.MIDDLEWARE.append('corsheaders.middleware.CorsMiddleware')
            
        if 'oauth2_provider.middleware.OAuth2TokenMiddleware' not in settings.MIDDLEWARE:
            self.stdout.write(self.style.NOTICE('Adding oauth2_provider.middleware.OAuth2TokenMiddleware to MIDDLEWARE in settings.py file.'))
            settings.MIDDLEWARE.append('oauth2_provider.middleware.OAuth2TokenMiddleware')
            
        # check for site variables
        if not hasattr(settings, 'SITE_DOMAIN'):
            self.stdout.write(self.style.NOTICE('Adding SITE_DOMAIN to settings.py file.'))
            settings.SITE_DOMAIN = site_domain
            
        if not hasattr(settings, 'SITE_NAME'):
            self.stdout.write(self.style.NOTICE('Adding SITE_NAME to settings.py file.'))
            settings.SITE_NAME = site_name
            
        if not hasattr(settings, 'SITE_LOGO'):
            self.stdout.write(self.style.NOTICE('Adding SITE_LOGO to settings.py file.'))
            settings.SITE_LOGO = ''
            
        if not hasattr(settings, 'SITE_LOGO_WHITE'):
            self.stdout.write(self.style.NOTICE('Adding SITE_LOGO_WHITE to settings.py file.'))
            settings.SITE_LOGO_WHITE = ''
            
        if not hasattr(settings, 'SITE_LOGO_BLACK'):
            self.stdout.write(self.style.NOTICE('Adding SITE_LOGO_BLACK to settings.py file.'))
            settings.SITE_LOGO_BLACK = ''
            
        if not hasattr(settings, 'SITE_DESCRIPTION'):
            self.stdout.write(self.style.NOTICE('Adding SITE_DESCRIPTION to settings.py file.'))
            settings.SITE_DESCRIPTION = ''
            
        # check for celery settings
        if not hasattr(settings, 'CELERY_BROKER_URL'):
            self.stdout.write(self.style.NOTICE('Adding CELERY_BROKER_URL to settings.py file.'))
            settings.CELERY_BROKER_URL = 'redis://localhost:6379/0'
        
        if not hasattr(settings, 'CELERY_RESULT_BACKEND'):
            self.stdout.write(self.style.NOTICE('Adding CELERY_RESULT_BACKEND to settings.py file.'))
            settings.CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
            
        if not hasattr(settings, 'CELERY_ACCEPT_CONTENT'):
            self.stdout.write(self.style.NOTICE('Adding CELERY_ACCEPT_CONTENT to settings.py file.'))
            settings.CELERY_ACCEPT_CONTENT = ['application/json']
            
        if not hasattr(settings, 'CELERY_RESULT_SERIALIZER'):
            self.stdout.write(self.style.NOTICE('Adding CELERY_RESULT_SERIALIZER to settings.py file.'))
            settings.CELERY_RESULT_SERIALIZER = 'json'
            
        if not hasattr(settings, 'CELERY_TIMEZONE'):
            self.stdout.write(self.style.NOTICE('Adding CELERY_TIMEZONE to settings.py file.'))
            settings.CELERY_TIMEZONE = settings.TIME_ZONE
            
        if not hasattr(settings, 'CELERY_TASK_SERIALIZER'):
            self.stdout.write(self.style.NOTICE('Adding CELERY_TASK_SERIALIZER to settings.py file.'))
            settings.CELERY_TASK_SERIALIZER = 'json'
            
        # check for ENV
        if not hasattr(settings, 'ENV'):
            self.stdout.write(self.style.NOTICE('Adding ENV to settings.py file.'))
            settings.ENV = os.getenv('DJANGO_ENV')
            
        # check for settings_[ENV].py
        if settings.ENV:
            if not os.path.exists(os.path.join(base_dir, f'{project_name}/settings_{settings.ENV}.py')):
                self.stdout.write(self.style.WARNING(f'{project_name}/settings_{settings.ENV}.py not found.'))
                
        #     CACHES = {
        #     'default': {
        #     'BACKEND': 'django.core.cache.backends.memcached.PyMemcacheCache',
        #     'LOCATION': '127.0.0.1:11211'
        #     }
        # }
        # check for cache settings
        if not hasattr(settings, 'CACHES'):
            self.stdout.write(self.style.NOTICE('Adding CACHES to settings.py file.'))
            settings.CACHES = {
                'default': {
                    'BACKEND': 'django.core.cache.backends.memcached.PyMemcacheCache',
                    'LOCATION': '127.0.0.1:11211'
                }
            }
        
        if not hasattr(settings, 'ASGI_APPLICATION'):
            self.stdout.write(self.style.NOTICE('Adding ASGI_APPLICATION to settings.py file.'))
            settings.ASGI_APPLICATION = f'{project_name}.asgi.application'
            
        if not hasattr(settings, 'CHANNEL_LAYERS'):
            #             CHANNEL_LAYERS = {
            #     'default': {
            #         'BACKEND': 'channels_redis.core.RedisChannelLayer',
            #         'CONFIG': {
            #             "hosts": [('127.0.0.1', 6379)],
            #             "capacity": 1500,
            #             "expiry": 10
            #         },
            #     },
            #     'dev': {
            #         "BACKEND": "channels.layers.InMemoryChannelLayer"
            #     }
            # }
            self.stdout.write(self.style.NOTICE('Adding CHANNEL_LAYERS to settings.py file.'))
            settings.CHANNEL_LAYERS = {
                'default': {
                    'BACKEND': 'channels_redis.core.RedisChannelLayer',
                    'CONFIG': {
                        "hosts": [('127.0.0.1', 6379)],
                        "capacity": 1500,
                        "expiry": 10
                    },
                },
                'dev': {
                    "BACKEND": "channels.layers.InMemoryChannelLayer"
                }
            }           
        
        if not hasattr(settings, 'SESSION_ENGINE'):
            self.stdout.write(self.style.NOTICE('Adding SESSION_ENGINE to settings.py file.'))
            settings.SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
            
        if not hasattr(settings, 'SESSION_COOKIE_NAME'):
            self.stdout.write(self.style.NOTICE('Adding SESSION_COOKIE_NAME to settings.py file.'))
            base_domain = settings.SITE_DOMAIN.split('.')
            settings.SESSION_COOKIE_NAME = f'{base_domain[0]}_session'
            
        if not hasattr(settings, 'SESSION_COOKIE_AGE'):
            self.stdout.write(self.style.NOTICE('Adding SESSION_COOKIE_AGE to settings.py file.'))
            settings.SESSION_COOKIE_AGE = 60 * 60 * 24 * 7
            
        if not hasattr(settings, 'SESSION_COOKIE_SECURE'):
            self.stdout.write(self.style.NOTICE('Adding SESSION_COOKIE_SECURE to settings.py file.'))
            settings.SESSION_COOKIE_SECURE = True
            
        if not hasattr(settings, 'SESSION_COOKIE_SAMESITE'):
            self.stdout.write(self.style.NOTICE('Adding SESSION_COOKIE_SAMESITE to settings.py file.'))
            settings.SESSION_COOKIE_SAMESITE = 'None'
            
        if not hasattr(settings, 'CACHE_MIDDLEWARE_KEY_PREFIX'):
            self.stdout.write(self.style.NOTICE('Adding CACHE_MIDDLEWARE_KEY_PREFIX to settings.py file.'))
            base_domain = settings.SITE_DOMAIN.split('.')
            settings.CACHE_MIDDLEWARE_KEY_PREFIX = f'{base_domain[0]}'
            
        if not hasattr(settings, 'AUTHENTICATION_BACKENDS'):
            self.stdout.write(self.style.NOTICE('Adding AUTHENTICATION_BACKENDS to settings.py file.'))
            settings.AUTHENTICATION_BACKENDS = [
                'oauth2_provider.backends.OAuth2Backend',
                'django.contrib.auth.backends.ModelBackend',             
            ]
        
        # create celery.py file
        celery_py = os.path.join(base_dir, f'{project_name}/celery.py')
        if not os.path.exists(celery_py) or force: 
            self.stdout.write(self.style.NOTICE('Creating celery.py file.'))
            with open(celery_py, 'w') as f:
                f.write(f"import os\n\n")
                f.write(f"from celery import Celery\n\n")
                f.write(f"os.environ.setdefault('DJANGO_SETTINGS_MODULE', '{project_name}.settings')\n\n")
                f.write(f"app = Celery('{project_name}')\n\n")
                f.write(f"app.config_from_object('django.conf:settings', namespace='CELERY')\n\n")
                f.write(f"app.autodiscover_tasks()\n")
        else:
            self.stdout.write(self.style.NOTICE('celery.py file already exists.'))
        
        # create asgi.py file
        asgi_py = os.path.join(base_dir, f'{project_name}/asgi.py')
        if not os.path.exists(asgi_py) or force:
            if os.path.exists(asgi_py) and force:
                # backup the file
                self.stdout.write(self.style.NOTICE(f'Backing up {asgi_py} file.'))
                
                os.rename(asgi_py, f'{asgi_py}_{time}.bak')
                
            self.stdout.write(self.style.NOTICE('Creating asgi.py file.'))
            with open(asgi_py, 'w') as f:
                f.write(f"\"\"\"\n")
                f.write(f"ASGI config for {project_name} project.\n\n")
                f.write(f"It exposes the ASGI callable as a module-level variable named ``application``.\n\n")
                f.write(f"For more information on this file, see\n")
                f.write(f"https://docs.djangoproject.com/en/4.1/howto/deployment/asgi/\n")
                f.write(f"\"\"\"\n\n")
                f.write(f"import os\n\n")
                f.write(f"from django.core.asgi import get_asgi_application\n")
                f.write(f"from nets_core.middleware.auth_token import AuthTokenMiddleware\n")
                f.write(f"from channels.routing import ProtocolTypeRouter, URLRouter\n\n")
                f.write(f"os.environ.setdefault('DJANGO_SETTINGS_MODULE', '{project_name}.settings')\n\n")
                f.write(f"django_asgi_application = get_asgi_application()\n\n")
                f.write(f"application = ProtocolTypeRouter({{\n")
                f.write(f"    \"http\": django_asgi_application,\n")
                f.write(f"    #\"websocket\": AuthTokenMiddleware(\n")
                f.write(f"        # URLRouter(\n")
                f.write(f"            # Just like the Django URL router, but for WebSockets\n")
                f.write(f"            # \"nets_core.routing.websocket_urlpatterns\"\n")
                f.write(f"    #   )\n")
                f.write(f"    # ),\n")
                f.write(f"}})\n")
                
        else:
            self.stdout.write(self.style.NOTICE('asgi.py file already exists.'))
            
        # create settings_[ENV].py file
        
        settings_env_py = os.path.join(base_dir, f'{project_name}/settings_nets.py')
        if not os.path.exists(settings_env_py) or force:
            if os.path.exists(settings_env_py)  and force:
                # backup the file
                self.stdout.write(self.style.NOTICE(f'Backing up {settings_env_py} file.'))
                
                os.rename(settings_env_py, f'{settings_env_py}_{time}.bak')
                    
            self.stdout.write(self.style.NOTICE(f'Creating settings_nets.py file.'))
            settings_content = ""
            for attr in dir(settings):
                if not attr in self.REQUIRE_SETTINGS:
                    continue
                if not attr.startswith('__'):
                    value = getattr(settings, attr)
                    if isinstance(value, str):
                        settings_content += f"{attr} = '{value}'\n"
                    elif isinstance(value, bool):
                        settings_content += f"{attr} = {value}\n"
                    elif isinstance(value, int):
                        settings_content += f"{attr} = {value}\n"
                    elif isinstance(value, list):
                        settings_content += f"{attr} = [\n"
                        for item in value:
                            settings_content += f"    '{item}',\n"
                        settings_content += "]\n"
                    elif isinstance(value, dict):
                        settings_content += f"{attr} = {json.dumps(value, indent=4, cls=SettingsEncoder)}\n"
                    elif isinstance(value, datetime):
                        settings_content += f"{attr} = datetime.datetime({value.year}, {value.month}, {value.day}, {value.hour}, {value.minute}, {value.second}, {value.microsecond})\n"
                        
            with open(settings_env_py, 'w') as f:
                f.write(settings_content)
        else:
            self.stdout.write(self.style.NOTICE(f'settings_nets.py file already exists.'))
            
        # append to settings file
        # check if setings_nets.py is already imported
        with open(os.path.join(base_dir, f'{project_name}/settings.py'), 'r') as f:
            settings_content = f.read()
            if 'from .settings_nets import *' in settings_content:
                self.stdout.write(self.style.SUCCESS(f'settings_nets.py already imported in settings.py file.'))
                return
            
        with open(os.path.join(base_dir, f'{project_name}/settings.py'), 'a') as f:
            f.write(f"\n\ntry:\n")
            f.write(f"    from .settings_nets import *\n")
            f.write(f"except ImportError:\n")
            f.write(f"    pass\n")

class SettingsEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, set):
            return list(obj)
        if isinstance(obj, Path):
            return str(obj)
        if isinstance(obj, type):
            return str(obj)
        if isinstance(obj, PosixPath):
            return str(obj)
        return json.JSONEncoder.default(self, obj)