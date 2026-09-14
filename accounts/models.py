"""
Models for the accounts app.

Defines the custom User model inheriting from AbstractUser,
and the EmailVerificationCode model for secure 6-digit email authentication.
"""

import re
import secrets
import string
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone


EDUCATION_CHOICES = [
    ("SSC", "SSC"),
    ("HSC", "HSC"),
    ("DIPLOMA", "Diploma"),
    ("BACHELOR", "Bachelor's"),
    ("MASTER", "Master's"),
    ("MPHIL", "MPhil"),
    ("PHD", "PhD"),
    ("OTHER", "Other"),
]


class CustomUserManager(BaseUserManager):
    """
    Custom user manager where email is the unique identifier for authentication
    instead of usernames.
    """

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular User with the given email and password."""
        if not email:
            raise ValueError("The Email address must be provided.")
        email = self.normalize_email(email)

        # Set default username to email if not explicitly provided
        username = extra_fields.pop("username", None)
        if not username:
            username = email.split("@")[0][:30]

        user = self.model(email=email, username=username, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_email_verified", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom User model representing system users.
    Identified primarily by unique email, with personal and educational details.
    """

    email = models.EmailField(
        verbose_name="Email Address",
        unique=True,
        db_index=True,
        max_length=255,
        help_text="Required. Primary email used for login and notifications.",
    )
    full_name = models.CharField(
        verbose_name="Full Name",
        max_length=150,
        help_text="Required. User's full legal name.",
    )
    date_of_birth = models.DateField(
        verbose_name="Date of Birth",
        null=True,
        blank=True,
        help_text="User's date of birth.",
    )
    mobile_number = models.CharField(
        verbose_name="Mobile Number",
        max_length=20,
        unique=True,
        db_index=True,
        help_text="Required. Unique mobile number (e.g. Bangladesh format).",
    )
    highest_education = models.CharField(
        verbose_name="Highest Education Level",
        max_length=20,
        choices=EDUCATION_CHOICES,
        default="BACHELOR",
        help_text="Highest completed education qualification.",
    )
    institution_name = models.CharField(
        verbose_name="Institution Name",
        max_length=255,
        blank=True,
        help_text="College, University, or Institute name.",
    )
    subject = models.CharField(
        verbose_name="Subject / Major",
        max_length=150,
        blank=True,
        help_text="Field of study or major subject.",
    )
    passing_year = models.PositiveIntegerField(
        verbose_name="Passing Year",
        null=True,
        blank=True,
        help_text="Year of completion / graduation.",
    )
    is_email_verified = models.BooleanField(
        verbose_name="Email Verified",
        default=False,
        help_text="Designates whether the user has verified their email address.",
    )
    is_active = models.BooleanField(
        verbose_name="Active Status",
        default=False,
        help_text="Designates whether this user should be treated as active.",
    )
    referral_code = models.CharField(
        verbose_name="Referral Code",
        max_length=12,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="Unique affiliate/referral code.",
    )
    referred_by = models.ForeignKey(
        "self",
        verbose_name="Referred By",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="direct_referrals",
        help_text="The sponsor who referred this user.",
    )
    updated_at = models.DateTimeField(
        verbose_name="Last Updated",
        auto_now=True,
    )

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-date_joined"]
        indexes = [
            models.Index(fields=["email"], name="idx_user_email"),
            models.Index(fields=["mobile_number"], name="idx_user_mobile"),
            models.Index(fields=["referral_code"], name="idx_user_ref_code"),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.email})"

    def clean(self):
        super().clean()
        if self.email:
            self.email = self.email.strip().lower()
        if self.full_name:
            self.full_name = self.full_name.strip()

    def save(self, *args, **kwargs):
        """
        Guarantees that a valid, unique username and unique referral_code are generated.
        """
        if not self.username:
            if self.email:
                base_username = re.sub(r"[^\w.@+-]", "", self.email.split("@")[0])[:25] or "user"
            else:
                base_username = "user"

            candidate = base_username
            counter = 1
            queryset = User.objects.filter(username__iexact=candidate)
            if self.pk:
                queryset = queryset.exclude(pk=self.pk)

            while queryset.exists():
                candidate = f"{base_username}_{counter}"
                counter += 1
                queryset = User.objects.filter(username__iexact=candidate)
                if self.pk:
                    queryset = queryset.exclude(pk=self.pk)

            self.username = candidate

        if not self.referral_code:
            alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
            while True:
                code = "".join(secrets.choice(alphabet) for _ in range(8))
                if not User.objects.filter(referral_code=code).exists():
                    self.referral_code = code
                    break

        super().save(*args, **kwargs)


class EmailVerificationCode(models.Model):
    """
    Stores 6-digit hashed email verification codes for secure user account verification.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="verification_codes",
        verbose_name="User",
    )
    code_hash = models.CharField(
        verbose_name="Hashed Verification Code",
        max_length=128,
        help_text="Cryptographically hashed verification code (never stored as plain text).",
    )
    expires_at = models.DateTimeField(
        verbose_name="Expiration Time",
        db_index=True,
        help_text="Time after which this verification code is no longer valid.",
    )
    attempts = models.PositiveIntegerField(
        verbose_name="Verification Attempts",
        default=0,
        help_text="Counter for invalid attempts to prevent brute-force attacks.",
    )
    is_used = models.BooleanField(
        verbose_name="Is Used",
        default=False,
        help_text="Marks whether this verification code has already been redeemed.",
    )
    created_at = models.DateTimeField(
        verbose_name="Created At",
        auto_now_add=True,
    )

    class Meta:
        verbose_name = "Email Verification Code"
        verbose_name_plural = "Email Verification Codes"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_used"], name="idx_verif_user_used"),
            models.Index(fields=["expires_at"], name="idx_verif_expires"),
        ]

    def __str__(self):
        status = "Used" if self.is_used else ("Expired" if self.is_expired() else "Active")
        return f"Code for {self.user.email} [{status}]"

    def is_expired(self):
        """Check if code has passed its expiration time."""
        return timezone.now() > self.expires_at

    def can_attempt(self, max_attempts=5):
        """Check if remaining attempts are within the allowed threshold."""
        return not self.is_used and not self.is_expired() and (self.attempts < max_attempts)
