# users/views.py

from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.views import View
from django.views.generic import RedirectView
from django.contrib.auth import logout
from django.urls import reverse_lazy
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.urls import default_urlpatterns


@login_required
def dashboard_view(request):
    """
    User dashboard view - only accessible to authenticated users
    """
    return render(request, 'users/dashboard.html', {
        'user': request.user
    })


def login_signup_view(request):
    """
    Show the login page with Google sign-in option
    """
    if request.user.is_authenticated:
        return redirect('users:dashboard')

    # Render the login template instead of redirecting
    return render(request, 'users/login_signup.html')


class LogoutView(View):
    """
    Custom logout view that prevents automatic redirection to Google login
    """

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            logout(request)
        return render(request, 'users/logout_success.html')
