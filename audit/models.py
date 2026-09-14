"""
Models for the audit logging application.

Tracks immutable security, administrative, and financial lifecycle events.
"""

from django.conf import settings
from django.db import models


ACTION_CHOICES = [
    ("USER_REGISTERED", "User Registered"),
    ("EMAIL_VERIFIED", "Email Verified"),
    ("LOGIN_SUCCESS", "Login Succeeded"),
    ("LOGIN_FAILED", "Login Failed"),
    ("PASSWORD_RESET", "Password Reset"),
    ("DEMO_DEPOSIT", "Demo Deposit Credited"),
    ("POSITION_CREATED", "Reward Position Allocated"),
    ("REWARD_CREDITED", "Daily Demo Reward Credited"),
    ("REFERRAL_REWARD", "Referral Reward Credited"),
    ("WITHDRAWAL_CREATED", "Withdrawal Requested"),
    ("WITHDRAWAL_APPROVED", "Withdrawal Approved"),
    ("WITHDRAWAL_REJECTED", "Withdrawal Rejected"),
    ("WITHDRAWAL_COMPLETED", "Withdrawal Completed"),
    ("ADMIN_ADJUSTMENT", "Admin Demo Adjustment"),
    ("POSITION_PAUSED", "Position Paused"),
    ("POSITION_RESUMED", "Position Resumed"),
    ("POSITION_CANCELLED", "Position Cancelled"),
]


class AuditLog(models.Model):
    """
    Immutable audit trail recording security and transaction lifecycle operations.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        verbose_name="Subject User",
    )
    admin_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="performed_admin_audits",
        verbose_name="Admin Actor",
    )
    action = models.CharField(
        verbose_name="Action Type",
        max_length=64,
        choices=ACTION_CHOICES,
        db_index=True,
    )
    entity_type = models.CharField(
        verbose_name="Entity Type",
        max_length=64,
        blank=True,
        help_text="e.g. Wallet, RewardPosition, Withdrawal.",
    )
    entity_id = models.CharField(
        verbose_name="Entity ID",
        max_length=64,
        blank=True,
    )
    description = models.TextField(
        verbose_name="Description",
    )
    ip_address = models.GenericIPAddressField(
        verbose_name="IP Address",
        null=True,
        blank=True,
    )
    user_agent = models.TextField(
        verbose_name="User Agent",
        blank=True,
    )
    created_at = models.DateTimeField(
        verbose_name="Timestamp",
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["action", "created_at"], name="idx_audit_action_date"),
            models.Index(fields=["user", "action"], name="idx_audit_user_action"),
        ]

    def __str__(self):
        actor = self.admin_user.email if self.admin_user else (self.user.email if self.user else "System")
        return f"[{self.action}] by {actor} at {self.created_at}"
