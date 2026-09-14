"""
URL patterns for the accounts application.
"""

from django.urls import path
from . import views

urlpatterns = [
    # Public & Onboarding
    path("", views.home_view, name="home"),
    path("register/", views.register_view, name="register"),
    path("verify-email/", views.verify_email_view, name="verify_email"),
    path("resend-verification/", views.resend_verification_code_view, name="resend_verification"),

    # Authentication
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    # Dashboard & Profile Management
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("profile/", views.profile_view, name="profile"),
    path("profile/edit/", views.edit_profile_view, name="edit_profile"),
    path("change-password/", views.change_password_view, name="change_password"),

    # Password Reset Flow
    path("forgot-password/", views.CustomPasswordResetView.as_view(), name="forgot_password"),
    path("forgot-password/done/", views.CustomPasswordResetDoneView.as_view(), name="password_reset_done"),
    path("reset-password/<uidb64>/<token>/", views.CustomPasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("reset-password/done/", views.CustomPasswordResetCompleteView.as_view(), name="password_reset_complete"),
]
