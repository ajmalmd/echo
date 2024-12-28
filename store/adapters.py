from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib import messages
from django.shortcuts import redirect
from allauth.exceptions import ImmediateHttpResponse
from django.contrib.auth import login
from .models import User  # Import your custom user model

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        """
        Handle Google login for existing users or new signups.
        """
        user = sociallogin.user  # The user instance from the social login
        if user.id:
            # User is already authenticated
            return

        try:
            # Check if a user with the same email exists
            existing_user = User.objects.get(email=user.email)
            # If a user exists, connect the social account and authenticate
            sociallogin.connect(request, existing_user)
            login(request, existing_user, backend='django.contrib.auth.backends.ModelBackend')
            if existing_user.fullname == '':
                existing_user.fullname = sociallogin.account.extra_data.get('name')
                existing_user.save()
            raise ImmediateHttpResponse(redirect('home'))  # Redirect to home page
        except User.DoesNotExist:
            # No existing user; continue to signup process
            pass

    def save_user(self, request, sociallogin, form=None):
        """
        Save the user during the signup process.
        - Set fullname if the user is signing up via Google for the first time.
        """
        user = super().save_user(request, sociallogin, form=form)
        new_user = User.objects.get(email=user.email)
        if new_user.fullname == '':
            new_user.fullname = sociallogin.account.extra_data.get('name')
            new_user.save()
        return user
