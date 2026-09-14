"""
Django Admin configuration for User and EmailVerificationCode models.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, EmailVerificationCode


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    """
    Custom admin interface for User model.
    Organizes personal, educational, authentication, and permission fields cleanly.
    """

    list_display = (
        "email",
        "full_name",
        "mobile_number",
        "highest_education",
        "is_email_verified",
        "is_active",
        "date_joined",
    )
    list_filter = (
        "is_email_verified",
        "is_active",
        "highest_education",
        "date_joined",
    )
    search_fields = (
        "email",
        "full_name",
        "mobile_number",
    )
    ordering = ("-date_joined",)

    fieldsets = (
        ("Authentication Credentials", {"fields": ("email", "password")}),
        (
            "Personal Information",
            {
                "fields": (
                    "full_name",
                    "date_of_birth",
                    "mobile_number",
                )
            },
        ),
        (
            "Education Background",
            {
                "fields": (
                    "highest_education",
                    "institution_name",
                    "subject",
                    "passing_year",
                )
            },
        ),
        (
            "Permissions & Status",
            {
                "fields": (
                    "is_email_verified",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important Dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "full_name",
                    "mobile_number",
                    "password1",
                    "password2",
                    "is_email_verified",
                    "is_active",
                ),
            },
        ),
    )


@admin.register(EmailVerificationCode)
class EmailVerificationCodeAdmin(admin.ModelAdmin):
    """
    Admin configuration for monitoring verification codes.
    Prevents unauthorized editing of code hashes.
    """

    list_display = (
        "user",
        "expires_at",
        "attempts",
        "is_used",
        "created_at",
    )
    list_filter = (
        "is_used",
        "created_at",
    )
    search_fields = (
        "user__email",
        "user__full_name",
    )
    readonly_fields = (
        "user",
        "code_hash",
        "expires_at",
        "attempts",
        "created_at",
    )
