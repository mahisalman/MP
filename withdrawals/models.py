"""
Models for the withdrawals application.

Simulates test withdrawals in virtual DUSD with status workflow, fund-locking,
and administrative approval without communicating with any external payment gateway.
"""

from decimal import Decimal
from django.conf import settings
from django.db import models


WITHDRAWAL_METHOD_CHOICES = [
    ("DEMO_BANK", "Demo Bank Transfer (Simulation)"),
    ("DEMO_MOBILE_WALLET", "Demo Mobile Wallet (Simulation)"),
    ("DEMO_CRYPTO", "Demo Crypto Address (Simulation)"),
]

WITHDRAWAL_STATUS_CHOICES = [
    ("PENDING", "Pending Approval"),
    ("APPROVED", "Approved"),
    ("PROCESSING", "Processing Simulation"),
    ("COMPLETED", "Completed (Simulation)"),
    ("REJECTED", "Rejected"),
    ("CANCELLED", "Cancelled"),
]


class Withdrawal(models.Model):
    """
    Simulated demo withdrawal request.
    Strictly educational / demonstration with no real monetary transfers.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="withdrawals",
        verbose_name="User",
    )
    wallet = models.ForeignKey(
        "wallet.Wallet",
        on_delete=models.CASCADE,
        related_name="withdrawals",
        verbose_name="Wallet",
    )
    amount = models.DecimalField(
        verbose_name="Requested Demo Amount",
        max_digits=18,
        decimal_places=2,
    )
    fee = models.DecimalField(
        verbose_name="Simulated Fee",
        max_digits=18,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    net_amount = models.DecimalField(
        verbose_name="Net Demo Amount",
        max_digits=18,
        decimal_places=2,
    )
    method = models.CharField(
        verbose_name="Simulated Payout Method",
        max_length=32,
        choices=WITHDRAWAL_METHOD_CHOICES,
        default="DEMO_MOBILE_WALLET",
    )
    account_name = models.CharField(
        verbose_name="Account Holder Name",
        max_length=150,
    )
    account_identifier = models.CharField(
        verbose_name="Account / Wallet Identifier",
        max_length=150,
        help_text="e.g. TEST-01712345678 or 0xDEMO...",
    )
    status = models.CharField(
        verbose_name="Status",
        max_length=20,
        choices=WITHDRAWAL_STATUS_CHOICES,
        default="PENDING",
        db_index=True,
    )
    requested_at = models.DateTimeField(auto_now_add=True, db_index=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="processed_withdrawals",
        verbose_name="Processed By",
    )
    admin_note = models.TextField(
        verbose_name="Admin Note",
        blank=True,
    )

    class Meta:
        verbose_name = "Demo Withdrawal"
        verbose_name_plural = "Demo Withdrawals"
        ordering = ["-requested_at"]
        indexes = [
            models.Index(fields=["user", "status"], name="idx_withdr_user_status"),
            models.Index(fields=["status", "requested_at"], name="idx_withdr_status_req"),
        ]

    def __str__(self):
        return f"Withdrawal #{self.id} - {self.amount} DUSD ({self.status})"
