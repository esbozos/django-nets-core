from . import views
from nets_core import google_auth, social_auth, openapi_views
from nets_core.routing import build_urlpatterns

app_name = 'nets_core_auth_api'

urlpatterns = [
    *build_urlpatterns(google_auth, social_auth, views, openapi_views),
]