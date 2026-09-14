"""
Forms for the accounts application.

Includes registration, login, verification, profile update, and password reset
with custom validators for Bangladesh mobile numbers, dates of birth, and passing years.
"""

import re
from datetime import date
from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import User, EDUCATION_CHOICES

# Bangladesh mobile number regex:
# Matches 013, 014, 015, 016, 017, 018, 019 with optional +88 or 88 country code prefix
BD_PHONE_REGEX = re.compile(r"^(?:\+?880|0)?(1[3-9]\d{8})$")


def normalize_bd_mobile(raw_mobile: str) -> str:
    """
    Validates and normalizes Bangladesh mobile numbers into standard international format (+8801XXXXXXXXX).
    Raises ValidationError if invalid.
    """
    clean_str = re.sub(r"[\s\-()]", "", raw_mobile.strip())
    match = BD_PHONE_REGEX.match(clean_str)
    if not match:
        raise ValidationError(
            "Please enter a valid Bangladesh mobile number (e.g. 01712345678 or +8801712345678)."
        )
    # Standardize to 01XXXXXXXXX or +8801XXXXXXXXX
    return f"+880{match.group(1)}"


class UserRegistrationForm(forms.ModelForm):
    """
    Registration form collecting personal info, education details, and password.
    """

    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Create a strong password"}),
        help_text="Must be at least 8 characters and not entirely numeric.",
    )
    confirm_password = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Confirm your password"}),
    )

    referral_code = forms.CharField(
        label="Referral Code (Optional)",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter sponsor's 8-character code"}),
        help_text="If you were invited by someone, enter their referral code here."
    )

    class Meta:
        model = User
        fields = [
            "full_name",
            "email",
            "date_of_birth",
            "mobile_number",
            "highest_education",
            "institution_name",
            "subject",
            "passing_year",
        ]
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Mahim Ahmed"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "e.g. mahim@example.com"}),
            "date_of_birth": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "mobile_number": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. 01712345678"}),
            "highest_education": forms.Select(attrs={"class": "form-select"}),
            "institution_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Dhaka University"}),
            "subject": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Computer Science & Engineering"}),
            "passing_year": forms.NumberInput(attrs={"class": "form-control", "placeholder": "e.g. 2023", "min": "1950", "max": "2035"}),
        }

    def clean_full_name(self):
        full_name = self.cleaned_data.get("full_name", "").strip()
        if len(full_name) < 2:
            raise ValidationError("Full name must be at least 2 characters long.")
        return full_name

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        if User.objects.filter(email=email).exists():
            raise ValidationError("An account with this email address already exists.")
        return email

    def clean_mobile_number(self):
        raw_mobile = self.cleaned_data.get("mobile_number", "")
        normalized_mobile = normalize_bd_mobile(raw_mobile)
        if User.objects.filter(mobile_number=normalized_mobile).exists():
            raise ValidationError("An account with this mobile number already exists.")
        return normalized_mobile

    def clean_date_of_birth(self):
        dob = self.cleaned_data.get("date_of_birth")
        if dob:
            today = date.today()
            if dob > today:
                raise ValidationError("Date of birth cannot be in the future.")
            # Calculate age
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            if age < 10:
                raise ValidationError("You must be at least 10 years old to register.")
            if age > 120:
                raise ValidationError("Please enter a realistic date of birth.")
        return dob

    def clean_passing_year(self):
        year = self.cleaned_data.get("passing_year")
        if year:
            current_year = date.today().year
            if year < 1950 or year > current_year + 10:
                raise ValidationError(f"Passing year must be between 1950 and {current_year + 10}.")
        return year

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password:
            if password != confirm_password:
                self.add_error("confirm_password", "Passwords do not match. Please verify and re-enter.")
            else:
                # Validate password with Django's configured password validators
                try:
                    validate_password(password)
                except ValidationError as error:
                    self.add_error("password", error)

        return cleaned_data


class EmailLoginForm(forms.Form):
    """
    Login form using Email and Password with Remember Me support.
    Provides generic error messaging to avoid email enumeration.
    """

    email = forms.EmailField(
        label="Email Address",
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "Enter your email", "autofocus": True}),
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Enter your password"}),
    )
    remember_me = forms.BooleanField(
        label="Remember me on this device",
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email", "").strip().lower()
        password = cleaned_data.get("password")

        if email and password:
            user = User.objects.filter(email=email).first()
            if user and user.check_password(password):
                self.user = user
            else:
                # Generic error message to prevent user enumeration
                raise ValidationError("Invalid email or password.")

        return cleaned_data


class VerifyEmailForm(forms.Form):
    """
    Form for validating the 6-digit email verification code.
    """

    code = forms.CharField(
        label="Verification Code",
        max_length=6,
        min_length=6,
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-lg text-center fw-bold fs-3 tracking-widest",
                "placeholder": "• • • • • •",
                "autocomplete": "one-time-code",
                "inputmode": "numeric",
                "pattern": "[0-9]{6}",
                "maxlength": "6",
                "autofocus": True,
            }
        ),
    )

    def clean_code(self):
        code = self.cleaned_data.get("code", "").strip()
        if not re.match(r"^\d{6}$", code):
            raise ValidationError("Verification code must be exactly 6 numeric digits.")
        return code


class UserProfileUpdateForm(forms.ModelForm):
    """
    Form for authenticated users to update their personal information and education background.
    Email and security fields are excluded and cannot be tampered with.
    """

    class Meta:
        model = User
        fields = [
            "full_name",
            "date_of_birth",
            "mobile_number",
            "highest_education",
            "institution_name",
            "subject",
            "passing_year",
        ]
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "form-control"}),
            "date_of_birth": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "mobile_number": forms.TextInput(attrs={"class": "form-control"}),
            "highest_education": forms.Select(attrs={"class": "form-select"}),
            "institution_name": forms.TextInput(attrs={"class": "form-control"}),
            "subject": forms.TextInput(attrs={"class": "form-control"}),
            "passing_year": forms.NumberInput(attrs={"class": "form-control", "min": "1950", "max": "2035"}),
        }

    def clean_full_name(self):
        full_name = self.cleaned_data.get("full_name", "").strip()
        if len(full_name) < 2:
            raise ValidationError("Full name must be at least 2 characters long.")
        return full_name

    def clean_mobile_number(self):
        raw_mobile = self.cleaned_data.get("mobile_number", "")
        normalized_mobile = normalize_bd_mobile(raw_mobile)
        existing = User.objects.filter(mobile_number=normalized_mobile).exclude(pk=self.instance.pk)
        if existing.exists():
            raise ValidationError("This mobile number is already in use by another account.")
        return normalized_mobile

    def clean_date_of_birth(self):
        dob = self.cleaned_data.get("date_of_birth")
        if dob:
            today = date.today()
            if dob > today:
                raise ValidationError("Date of birth cannot be in the future.")
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            if age < 10:
                raise ValidationError("You must be at least 10 years old.")
        return dob

    def clean_passing_year(self):
        year = self.cleaned_data.get("passing_year")
        if year:
            current_year = date.today().year
            if year < 1950 or year > current_year + 10:
                raise ValidationError(f"Passing year must be between 1950 and {current_year + 10}.")
        return year


class CustomPasswordResetForm(PasswordResetForm):
    """
    Customized Password Reset Form with Bootstrap 5 widgets.
    """

    email = forms.EmailField(
        label="Email Address",
        max_length=254,
        widget=forms.EmailInput(
            attrs={"class": "form-control", "placeholder": "Enter your registered email address", "autofocus": True}
        ),
    )


class CustomSetPasswordForm(SetPasswordForm):
    """
    Customized Set Password Form with Bootstrap 5 widgets.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({"class": "form-control"})
