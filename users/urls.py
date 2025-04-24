# users/urls.py
from django.urls import path
from . import views
from allauth.socialaccount.providers.google.views import oauth2_login

app_name = 'users'

urlpatterns = [
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('login/', views.login_signup_view, name='login_signup'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    # Add direct Google login URL
    path('google/login/', oauth2_login, name='google_login'),
]
