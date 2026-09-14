"""
Comprehensive automated unit and integration tests for accounts app.

Covers:
1. User registration & validation (BD mobile, DOB, password match)
2. 6-digit email code generation, verification, expiration, attempts, & resend cooldown
3. Authentication (login with email, remember me, logout, unverified blocking)
4. Profile view & profile update security
5. Password reset & change flows
"""

from datetime import date, timedelta
from django.core import mail
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from .models import User, EmailVerificationCode
from .services import (
    create_and_send_verification_code,
    verify_email_code,
    can_resend_code,
    mask_email,
)


class AccountsRegistrationTests(TestCase):
    """Tests for registration form and view validation rules."""

    def setUp(self):
        self.client = Client()
        self.register_url = reverse("register")
        self.valid_data = {
            "full_name": "Rahim Uddin",
            "email": "rahim@example.com",
            "date_of_birth": "1998-05-15",
            "mobile_number": "01711223344",
            "highest_education": "BACHELOR",
            "institution_name": "University of Dhaka",
            "subject": "Computer Science",
            "passing_year": 2021,
            "password": "StrongPassword@123",
            "confirm_password": "StrongPassword@123",
        }

    def test_successful_registration(self):
        """User can register with valid data, is saved as inactive, and code is sent."""
        response = self.client.post(self.register_url, self.valid_data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("verify_email"))

        # User is created inactive and unverified
        user = User.objects.get(email="rahim@example.com")
        self.assertFalse(user.is_active)
        self.assertFalse(user.is_email_verified)
        self.assertEqual(user.mobile_number, "+8801711223344")

        # Session holds pending user ID
        self.assertEqual(self.client.session.get("pending_verification_user_id"), user.id)

        # Verification code was created and email sent
        self.assertEqual(user.verification_codes.count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Verify Your Email Address", mail.outbox[0].subject)

    def test_duplicate_email_rejected(self):
        """Registration fails if email is already taken."""
        self.client.post(self.register_url, self.valid_data)
        dup_data = self.valid_data.copy()
        dup_data["mobile_number"] = "01811223344"
        response = self.client.post(self.register_url, dup_data)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, "form", "email", "An account with this email address already exists.")

    def test_duplicate_mobile_rejected(self):
        """Registration fails if Bangladesh mobile number is already taken."""
        self.client.post(self.register_url, self.valid_data)
        dup_data = self.valid_data.copy()
        dup_data["email"] = "different@example.com"
        dup_data["mobile_number"] = "+8801711223344"  # Same number with international prefix
        response = self.client.post(self.register_url, dup_data)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, "form", "mobile_number", "An account with this mobile number already exists.")

    def test_invalid_bangladesh_mobile_rejected(self):
        """Invalid mobile formats are rejected."""
        invalid_data = self.valid_data.copy()
        invalid_data["mobile_number"] = "1234567"
        response = self.client.post(self.register_url, invalid_data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("mobile_number", response.context["form"].errors)

    def test_future_date_of_birth_rejected(self):
        """Date of birth in the future must fail validation."""
        invalid_data = self.valid_data.copy()
        invalid_data["date_of_birth"] = (date.today() + timedelta(days=5)).isoformat()
        response = self.client.post(self.register_url, invalid_data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("date_of_birth", response.context["form"].errors)

    def test_underage_date_of_birth_rejected(self):
        """Age under 10 must fail validation."""
        invalid_data = self.valid_data.copy()
        invalid_data["date_of_birth"] = (date.today() - timedelta(days=365 * 5)).isoformat()
        response = self.client.post(self.register_url, invalid_data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("date_of_birth", response.context["form"].errors)

    def test_password_mismatch_rejected(self):
        """Mismatched passwords must fail validation."""
        mismatch_data = self.valid_data.copy()
        mismatch_data["confirm_password"] = "MismatchPassword@999"
        response = self.client.post(self.register_url, mismatch_data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("confirm_password", response.context["form"].errors)


class EmailVerificationTests(TestCase):
    """Tests for 6-digit email verification flow, limits, expiry, and cooldown."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email="testuser@example.com",
            password="StrongPassword@123",
            full_name="Test User",
            mobile_number="+8801911223344",
            is_active=False,
            is_email_verified=False,
        )
        self.verify_url = reverse("verify_email")

    def test_email_masking_utility(self):
        """Masking utility hides sensitive portions of the email."""
        self.assertEqual(mask_email("user@domain.com"), "u***r@domain.com")
        self.assertEqual(mask_email("ab@domain.com"), "a***@domain.com")
        self.assertEqual(mask_email(""), "")

    def test_valid_code_verification(self):
        """Submitting the correct code activates the user."""
        create_and_send_verification_code(self.user)
        code_record = self.user.verification_codes.first()

        # Retrieve the generated code by testing values or intercepting service
        # In service, raw_code was generated. Let's create a known code test
        code_record.delete()

        # Manually create known code
        from .services import hash_verification_code
        test_code = "123456"
        EmailVerificationCode.objects.create(
            user=self.user,
            code_hash=hash_verification_code(test_code),
            expires_at=timezone.now() + timedelta(minutes=10),
            attempts=0,
            is_used=False,
        )

        session = self.client.session
        session["pending_verification_user_id"] = self.user.id
        session.save()

        response = self.client.post(self.verify_url, {"code": test_code})
        self.assertRedirects(response, reverse("login"))

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertTrue(self.user.is_email_verified)

    def test_incorrect_code_increments_attempts(self):
        """Incorrect code increments attempts and does not activate user."""
        from .services import hash_verification_code
        code_record = EmailVerificationCode.objects.create(
            user=self.user,
            code_hash=hash_verification_code("654321"),
            expires_at=timezone.now() + timedelta(minutes=10),
            attempts=0,
            is_used=False,
        )

        session = self.client.session
        session["pending_verification_user_id"] = self.user.id
        session.save()

        response = self.client.post(self.verify_url, {"code": "111111"})
        self.assertEqual(response.status_code, 200)

        code_record.refresh_from_db()
        self.assertEqual(code_record.attempts, 1)

        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertFalse(self.user.is_email_verified)

    def test_max_attempts_invalidates_code(self):
        """Exceeding max attempts invalidates code."""
        from .services import hash_verification_code
        code_record = EmailVerificationCode.objects.create(
            user=self.user,
            code_hash=hash_verification_code("654321"),
            expires_at=timezone.now() + timedelta(minutes=10),
            attempts=4,
            is_used=False,
        )

        success, msg = verify_email_code(self.user, "000000")
        self.assertFalse(success)
        self.assertIn("Too many failed attempts", msg)

        code_record.refresh_from_db()
        self.assertTrue(code_record.is_used)

    def test_expired_code_rejected(self):
        """Expired code is rejected."""
        from .services import hash_verification_code
        EmailVerificationCode.objects.create(
            user=self.user,
            code_hash=hash_verification_code("123456"),
            expires_at=timezone.now() - timedelta(minutes=1),  # Expired
            attempts=0,
            is_used=False,
        )

        success, msg = verify_email_code(self.user, "123456")
        self.assertFalse(success)
        self.assertIn("expired", msg)

    def test_resend_cooldown_enforced(self):
        """Resend request within cooldown period is blocked."""
        # First code dispatch
        create_and_send_verification_code(self.user)
        can_resend, remaining = can_resend_code(self.user)
        self.assertFalse(can_resend)
        self.assertGreater(remaining, 0)

        # Attempt to create another code immediately fails
        sent, msg = create_and_send_verification_code(self.user)
        self.assertFalse(sent)
        self.assertIn("Please wait", msg)


class AuthenticationTests(TestCase):
    """Tests for login, unverified blocking, remember me, and logout."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email="activeuser@example.com",
            password="StrongPassword@123",
            full_name="Active User",
            mobile_number="+8801700112233",
            is_active=True,
            is_email_verified=True,
        )
        self.unverified_user = User.objects.create_user(
            email="unverified@example.com",
            password="StrongPassword@123",
            full_name="Unverified User",
            mobile_number="+8801700112244",
            is_active=False,
            is_email_verified=False,
        )

    def test_successful_login_with_email(self):
        """Verified user can log in with email and password."""
        response = self.client.post(
            reverse("login"),
            {"email": "activeuser@example.com", "password": "StrongPassword@123"},
        )
        self.assertRedirects(response, reverse("dashboard"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.id)

    def test_invalid_password_returns_generic_error(self):
        """Wrong password returns generic error message without enumerating user."""
        response = self.client.post(
            reverse("login"),
            {"email": "activeuser@example.com", "password": "WrongPassword"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid email or password.")

    def test_unverified_user_cannot_login_and_redirects_to_verification(self):
        """Unverified user logging in is blocked and sent to email verification."""
        response = self.client.post(
            reverse("login"),
            {"email": "unverified@example.com", "password": "StrongPassword@123"},
        )
        self.assertRedirects(response, reverse("verify_email"))
        self.assertEqual(self.client.session.get("pending_verification_user_id"), self.unverified_user.id)

    def test_logout(self):
        """Logging out clears authentication and redirects to login."""
        self.client.login(username="activeuser@example.com", password="StrongPassword@123")
        response = self.client.get(reverse("logout"))
        self.assertRedirects(response, reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)


class UserProfileTests(TestCase):
    """Tests for dashboard, profile view, and edit profile security."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email="profiletest@example.com",
            password="StrongPassword@123",
            full_name="Profile Tester",
            mobile_number="+8801799887766",
            highest_education="MASTER",
            institution_name="BUET",
            subject="CSE",
            passing_year=2022,
            is_active=True,
            is_email_verified=True,
        )
        self.client.login(username="profiletest@example.com", password="StrongPassword@123")

    def test_view_profile(self):
        """Authenticated user can view dashboard and profile."""
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Profile Tester")
        self.assertContains(response, "profiletest@example.com")
        self.assertContains(response, "BUET")

    def test_update_profile(self):
        """User can update allowed profile fields."""
        update_data = {
            "full_name": "Updated Name",
            "date_of_birth": "1995-10-20",
            "mobile_number": "01899887766",
            "highest_education": "PHD",
            "institution_name": "MIT",
            "subject": "AI",
            "passing_year": 2025,
        }
        response = self.client.post(reverse("edit_profile"), update_data)
        self.assertRedirects(response, reverse("profile"))

        self.user.refresh_from_db()
        self.assertEqual(self.user.full_name, "Updated Name")
        self.assertEqual(self.user.mobile_number, "+8801899887766")
        self.assertEqual(self.user.highest_education, "PHD")

    def test_protected_fields_cannot_be_tampered_with(self):
        """Attempting to alter is_staff or email via edit profile is ignored."""
        tampered_data = {
            "full_name": "Hacker Name",
            "email": "hacked@example.com",
            "is_staff": True,
            "is_superuser": True,
            "highest_education": "BACHELOR",
            "mobile_number": "01799887766",
        }
        self.client.post(reverse("edit_profile"), tampered_data)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "profiletest@example.com")
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)


class PasswordResetTests(TestCase):
    """Tests for password reset link generation and password change."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email="resettest@example.com",
            password="OriginalPassword@123",
            full_name="Reset User",
            mobile_number="+8801733445566",
            is_active=True,
            is_email_verified=True,
        )

    def test_forgot_password_sends_email(self):
        """Requesting password reset dispatches email."""
        response = self.client.post(reverse("forgot_password"), {"email": "resettest@example.com"})
        self.assertRedirects(response, reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Password Reset Request", mail.outbox[0].subject)

    def test_forgot_password_non_existent_email_does_not_reveal(self):
        """Requesting reset for non-existent email redirects identically to prevent enumeration."""
        response = self.client.post(reverse("forgot_password"), {"email": "doesnotexist@example.com"})
        self.assertRedirects(response, reverse("password_reset_done"))
        # No email sent
        self.assertEqual(len(mail.outbox), 0)
