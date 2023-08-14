from django.urls import path
from . import views
app_name = 'nets_core_auth_api'

urlpatterns = [
    path('login/', views.auth_login, name='login'),
    path('logout/', views.auth_logout, name='logout'),
    path('authenticate/', views.auth, name='authenticate'),
    path('update/', views.update_user, name='update'),
]