from django.urls import path
from nets_core.google_auth import login_with_google
from nets_core.social_auth import (
    login_with_apple,
    login_with_facebook,
    login_with_google_social,
    login_with_github,
    login_with_microsoft,
)
from . import views

app_name = 'nets_core_auth_api'

urlpatterns = [
    path('loginWithGoogle/', login_with_google, name='loginWithGoogle'),
    path('loginWithGoogleSocial/', login_with_google_social, name='loginWithGoogleSocial'),
    path('loginWithApple/', login_with_apple, name='loginWithApple'),
    path('loginWithFacebook/', login_with_facebook, name='loginWithFacebook'),
    path('loginWithMicrosoft/', login_with_microsoft, name='loginWithMicrosoft'),
    path('loginWithGithub/', login_with_github, name='loginWithGithub'),
    path('login/', views.auth_login, name='login'),
    path('logout/', views.auth_logout, name='logout'),
    path('authenticate/', views.auth, name='authenticate'),
    path('update/', views.update_user, name='update'),
    path('getProfile/', views.auth_get_profile, name='getProfile'),
    path('requestDelete/', views.request_delete_user_account, name='requestDelete'),
    path('delete/', views.delete_user_account, name='delete'),
]