import os

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "oauth2_provider",
    "nets_core",
    "nets_core_tests",
]
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": os.environ["DB_HOST"],
        "PORT": os.environ["DB_PORT"],
        "NAME": os.environ["DB_NAME"],
        "USER": os.environ["DB_USER"],
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "TEST": {"NAME": os.environ["DB_TEST_NAME"]},
    }
}
ROOT_URLCONF = __name__
urlpatterns = []
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
NETS_CORE_TO_JSON_BACKEND = "python"
USE_TZ = True
TIME_ZONE = "UTC"
