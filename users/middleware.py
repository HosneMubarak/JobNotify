# users/middleware.py
from django.shortcuts import redirect
from django.urls import resolve, reverse


class RedirectMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Process request before view is called
        path = request.path_info

        # Redirect standard allauth login/signup pages to our custom login
        if path in ['/accounts/login/', '/accounts/signup/']:
            return redirect(reverse('users:login_signup'))

        response = self.get_response(request)
        return response
