"""
Business logic and service operations for authentication and email verification.

Separates core security and business rules from HTTP views to ensure
modularity, testability, and clean code architecture.
"""

import hashlib
import hmac
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone

from .models import EmailVerificationCode

logger = logging.getLogger("accounts")


def generate_verification_code() -> str:
    """
    Generates a secure 6-digit numeric verification code using Python's secrets module.
    """
    # Generate 6 random digits between 100000 and 999999
    code_int = secrets.randbelow(900000) + 100000
    return str(code_int)


def hash_verification_code(code: str) -> str:
    """
    Produces a SHA-256 HMAC digest of the verification code using the application's SECRET_KEY.
    Ensures that plain-text codes are never stored in the database.
    """
    key = settings.SECRET_KEY.encode("utf-8")
    data = code.strip().encode("utf-8")
    return hmac.new(key, data, hashlib.sha256).hexdigest()


def verify_code_hash(raw_code: str, stored_hash: str) -> bool:
    """
    Performs constant-time comparison of a user-supplied code against a stored HMAC hash.
    Protects against timing attacks.
    """
    computed_hash = hash_verification_code(raw_code)
    return hmac.compare_digest(computed_hash, stored_hash)


def mask_email(email: str) -> str:
    """
    Partially masks an email address for privacy display.
    Example: 'mahim@example.com' -> 'm***m@example.com'
    """
    if not email or "@" not in email:
        return email

    name_part, domain_part = email.split("@", 1)
    if len(name_part) <= 2:
        masked_name = name_part[0] + "***"
    else:
        masked_name = name_part[0] + "***" + name_part[-1]

    return f"{masked_name}@{domain_part}"


def can_resend_code(user) -> tuple[bool, int]:
    """
    Checks if enough time has passed since the last verification code was sent.
    Returns (can_resend: bool, remaining_seconds: int).
    """
    cooldown_seconds = getattr(settings, "VERIFICATION_CODE_RESEND_COOLDOWN_SECONDS", 45)
    latest_code = user.verification_codes.order_by("-created_at").first()

    if not latest_code:
        return True, 0

    elapsed = (timezone.now() - latest_code.created_at).total_seconds()
    if elapsed < cooldown_seconds:
        remaining = int(cooldown_seconds - elapsed)
        return False, max(1, remaining)

    return True, 0


def create_and_send_verification_code(user, request=None) -> tuple[bool, str]:
    """
    Generates a secure verification code, records it, invalidates older unused codes,
    and dispatches an email to the user.
    """
    can_send, remaining_seconds = can_resend_code(user)
    if not can_send:
        return False, f"Please wait {remaining_seconds} seconds before requesting a new code."

    # Invalidate previous unused codes for this user
    user.verification_codes.filter(is_used=False).update(is_used=True)

    # Generate and hash new 6-digit code
    raw_code = generate_verification_code()
    code_hash = hash_verification_code(raw_code)

    expiry_minutes = getattr(settings, "VERIFICATION_CODE_EXPIRY_MINUTES", 10)
    expires_at = timezone.now() + timedelta(minutes=expiry_minutes)

    EmailVerificationCode.objects.create(
        user=user,
        code_hash=code_hash,
        expires_at=expires_at,
        attempts=0,
        is_used=False,
    )

    # Render email context
    context = {
        "user": user,
        "verification_code": raw_code,
        "expiry_minutes": expiry_minutes,
    }
    subject = "Verify Your Email Address - Django Auth Portal"
    text_message = render_to_string("accounts/emails/verification_email.txt", context)
    html_message = render_to_string("accounts/emails/verification_email.html", context)

    try:
        send_mail(
            subject=subject,
            message=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info("Verification code dispatched to user_id=%s (email masked: %s)", user.id, mask_email(user.email))
        if settings.DEBUG:
            logger.info("[DEVELOPMENT MODE CODE] The 6-digit verification code for %s is: %s", user.email, raw_code)
            if request and hasattr(request, "session"):
                request.session["dev_verification_code"] = raw_code
        return True, "A 6-digit verification code has been sent to your email."
    except Exception as exc:
        logger.error("Failed to send verification email to user_id=%s: %s", user.id, str(exc))
        return False, "Failed to send email. Please try again or contact support."


def verify_email_code(user, submitted_code: str) -> tuple[bool, str]:
    """
    Validates a submitted 6-digit verification code against the active database record.
    Enforces expiry, single-use, and maximum verification attempts.
    """
    clean_code = submitted_code.strip()
    max_attempts = getattr(settings, "VERIFICATION_CODE_MAX_ATTEMPTS", 5)

    # Retrieve the latest active code
    code_record = user.verification_codes.filter(is_used=False).order_by("-created_at").first()

    if not code_record:
        return False, "No active verification code found. Please request a new code."

    if code_record.is_expired():
        code_record.is_used = True
        code_record.save(update_fields=["is_used"])
        logger.info("Verification attempt with expired code for user_id=%s", user.id)
        return False, "The verification code has expired. Please request a new code."

    if code_record.attempts >= max_attempts:
        code_record.is_used = True
        code_record.save(update_fields=["is_used"])
        logger.warning("Too many verification attempts for user_id=%s; code invalidated", user.id)
        return False, "Too many failed attempts. This code has been invalidated. Please request a new code."

    # Validate code hash
    if not verify_code_hash(clean_code, code_record.code_hash):
        code_record.attempts += 1
        code_record.save(update_fields=["attempts"])
        remaining = max_attempts - code_record.attempts
        logger.info(
            "Incorrect verification code entered for user_id=%s. Attempts left: %s",
            user.id,
            remaining,
        )
        if remaining <= 0:
            code_record.is_used = True
            code_record.save(update_fields=["is_used"])
            return False, "Too many failed attempts. Please request a new verification code."
        return False, f"The verification code is incorrect. You have {remaining} attempt(s) remaining."

    # Successful verification
    code_record.is_used = True
    code_record.save(update_fields=["is_used"])

    user.is_email_verified = True
    user.is_active = True
    user.save(update_fields=["is_email_verified", "is_active", "updated_at"])

    logger.info("User id=%s successfully verified their email address.", user.id)
    return True, "Your email has been verified successfully. You can now log in."
