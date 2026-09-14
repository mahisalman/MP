"""
Views for the accounts application.

Handles registration, email verification, authentication, profile management,
and password reset flows with clean separation from services.
"""

import logging
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.views import (
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
)
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST, require_http_methods

from .forms import (
    UserRegistrationForm,
    EmailLoginForm,
    VerifyEmailForm,
    UserProfileUpdateForm,
    CustomPasswordResetForm,
    CustomSetPasswordForm,
)
from .models import User
from .services import (
    create_and_send_verification_code,
    verify_email_code,
    can_resend_code,
    mask_email,
)

logger = logging.getLogger("accounts")


def home_view(request):
    """Public landing page displaying features and onboarding links."""
    return render(request, "home.html")


def register_view(request):
    """
    Handles user registration.
    Upon successful validation, creates an inactive/unverified user,
    dispatches a 6-digit email verification code, and redirects to the verification page.
    """
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.is_email_verified = False
            user.set_password(form.cleaned_data["password"])
            user.save()

            # Store pending verification user id in session
            request.session["pending_verification_user_id"] = user.id

            # Generate and send 6-digit verification code
            sent, msg = create_and_send_verification_code(user, request)
            if sent:
                messages.success(request, "Registration successful! Please enter the 6-digit code sent to your email.")
            else:
                messages.warning(request, f"Registration recorded, but email dispatch failed: {msg}")

            logger.info("New registration initialized for user id=%s (email=%s)", user.id, user.email)
            return redirect("verify_email")
    else:
        form = UserRegistrationForm()

    return render(request, "accounts/register.html", {"form": form})


def verify_email_view(request):
    """
    Renders verification code input screen and validates the submitted 6-digit code.
    Enforces maximum attempts and expiration.
    """
    # Identify the user attempting verification
    user = None
    pending_user_id = request.session.get("pending_verification_user_id")

    if pending_user_id:
        user = User.objects.filter(id=pending_user_id).first()
    elif request.user.is_authenticated and not request.user.is_email_verified:
        user = request.user

    if not user:
        messages.info(request, "Please register or log in with your credentials to verify your email.")
        return redirect("login")

    # If already verified, direct to login
    if user.is_email_verified and user.is_active:
        messages.info(request, "Your email is already verified. Please log in.")
        return redirect("login")

    can_resend, remaining_seconds = can_resend_code(user)
    masked_email = mask_email(user.email)

    if request.method == "POST":
        form = VerifyEmailForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data["code"]
            success, msg = verify_email_code(user, code)
            if success:
                # Clear session state
                request.session.pop("pending_verification_user_id", None)
                messages.success(request, msg)
                return redirect("login")
            else:
                messages.error(request, msg)
                form.add_error("code", msg)
    else:
        form = VerifyEmailForm()

    dev_code = request.session.get("dev_verification_code") if settings.DEBUG else None
    is_console_email = "console" in getattr(settings, "EMAIL_BACKEND", "").lower()

    context = {
        "form": form,
        "masked_email": masked_email,
        "can_resend": can_resend,
        "remaining_seconds": remaining_seconds,
        "dev_code": dev_code,
        "is_console_email": is_console_email,
    }
    return render(request, "accounts/verify_email.html", context)


@require_POST
def resend_verification_code_view(request):
    """
    Resends a new 6-digit verification code if cooldown has elapsed.
    """
    user = None
    pending_user_id = request.session.get("pending_verification_user_id")

    if pending_user_id:
        user = User.objects.filter(id=pending_user_id).first()
    elif request.user.is_authenticated and not request.user.is_email_verified:
        user = request.user

    if not user:
        messages.error(request, "Session expired or invalid user. Please register or log in.")
        return redirect("login")

    sent, msg = create_and_send_verification_code(user, request)
    if sent:
        messages.success(request, msg)
    else:
        messages.warning(request, msg)

    return redirect("verify_email")


def login_view(request):
    """
    Authenticates user via Email and Password.
    Verifies email verification status and handles Remember Me.
    """
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = EmailLoginForm(request.POST)
        if form.is_valid():
            user = getattr(form, "user", None)
            if user:
                # Check email verification status
                if not user.is_email_verified:
                    request.session["pending_verification_user_id"] = user.id
                    create_and_send_verification_code(user, request)
                    messages.warning(
                        request,
                        "Your email is not yet verified. A fresh verification code has been sent to your email.",
                    )
                    return redirect("verify_email")

                if not user.is_active:
                    messages.error(request, "Your account has been deactivated. Please contact the administrator.")
                    return render(request, "accounts/login.html", {"form": form})

                # Perform login
                auth_login(request, user)

                # Handle Remember Me
                remember_me = form.cleaned_data.get("remember_me", False)
                if remember_me:
                    request.session.set_expiry(1209600)  # 2 weeks
                else:
                    request.session.set_expiry(0)  # On browser close

                messages.success(request, f"Welcome back, {user.full_name}!")

                # Redirect to next parameter if safe, else to dashboard
                redirect_to = request.POST.get("next") or request.GET.get("next")
                if redirect_to and url_has_allowed_host_and_scheme(
                    url=redirect_to,
                    allowed_hosts={request.get_host()},
                    require_https=request.is_secure(),
                ):
                    return redirect(redirect_to)

                return redirect("dashboard")
    else:
        form = EmailLoginForm()

    return render(request, "accounts/login.html", {"form": form})


def logout_view(request):
    """Logs out the user and redirects to login with a confirmation notice."""
    auth_logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect("login")


@login_required
def dashboard_view(request):
    """Dashboard homepage for authenticated users."""
    return render(request, "accounts/dashboard.html", {"user": request.user})


@login_required
def profile_view(request):
    """Full user profile display with personal and educational details."""
    return render(request, "accounts/profile.html", {"user": request.user})


@login_required
def edit_profile_view(request):
    """Allows updating personal and educational details, keeping sensitive fields immutable."""
    if request.method == "POST":
        form = UserProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated successfully.")
            return redirect("profile")
    else:
        form = UserProfileUpdateForm(instance=request.user)

    return render(request, "accounts/edit_profile.html", {"form": form})


@login_required
def change_password_view(request):
    """Allows logged-in users to update their password while preserving session login."""
    if request.method == "POST":
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Keep user logged in
            messages.success(request, "Your password has been changed successfully.")
            return redirect("profile")
    else:
        form = PasswordChangeForm(user=request.user)

    # Style form controls
    for field in form.fields.values():
        field.widget.attrs.update({"class": "form-control"})

    return render(request, "accounts/change_password.html", {"form": form})


# Password Reset Views using Django's built-in auth flow with custom Bootstrap templates
class CustomPasswordResetView(PasswordResetView):
    form_class = CustomPasswordResetForm
    template_name = "accounts/forgot_password.html"
    email_template_name = "accounts/emails/password_reset_email.txt"
    html_email_template_name = "accounts/emails/password_reset_email.html"
    subject_template_name = "accounts/emails/password_reset_subject.txt"
    success_url = reverse_lazy("password_reset_done")


class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = "accounts/forgot_password_done.html"


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    form_class = CustomSetPasswordForm
    template_name = "accounts/reset_password.html"
    success_url = reverse_lazy("password_reset_complete")


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = "accounts/reset_password_complete.html"
