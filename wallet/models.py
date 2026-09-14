"""
Models for the wallet application.

Implements the user's virtual demo wallet and an append-only transaction ledger
with unique idempotency keys, financial Decimal precision, and row-locking support.
"""

from decimal import Decimal
from django.conf import settings
from django.db import models


TRANSACTION_TYPE_CHOICES = [
    ("DEMO_DEPOSIT", "Demo Deposit"),
    ("DEMO_POSITION_ALLOCATION", "Demo Position Allocation"),
    ("DEMO_REWARD", "Daily Demo Reward"),
    ("REFERRAL_REWARD", "Demo Referral Reward"),
    ("DEMO_WITHDRAWAL", "Demo Withdrawal"),
    ("WITHDRAWAL_REVERSAL", "Withdrawal Reversal"),
    ("REFUND", "Refund"),
    ("ADMIN_ADJUSTMENT", "Admin Demo Adjustment"),
    ("REVERSAL", "Reversal"),
]

DIRECTION_CHOICES = [
    ("CREDIT", "Credit"),
    ("DEBIT", "Debit"),
]


class Wallet(models.Model):
    """
    Virtual Demo Wallet holding test DUSD balances.
    Strictly isolated from real currency or payment gateways.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wallet",
        verbose_name="User",
    )
    currency = models.CharField(
        verbose_name="Currency Code",
        max_length=10,
        default="DUSD",
        help_text="Virtual demo currency identifier (e.g. DUSD).",
    )
    available_balance = models.DecimalField(
        verbose_name="Available Demo Balance",
        max_digits=18,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Simulated balance available for demo allocations or withdrawals.",
    )
    locked_balance = models.DecimalField(
        verbose_name="Locked Demo Balance",
        max_digits=18,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Simulated balance held pending withdrawal approval or active lock.",
    )
    lifetime_credited = models.DecimalField(
        verbose_name="Lifetime Demo Credited",
        max_digits=18,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    lifetime_debited = models.DecimalField(
        verbose_name="Lifetime Demo Debited",
        max_digits=18,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Demo Wallet"
        verbose_name_plural = "Demo Wallets"
        indexes = [
            models.Index(fields=["user"], name="idx_wallet_user"),
        ]

    def __str__(self):
        return f"{self.user.email} Wallet ({self.available_balance} {self.currency})"

    @property
    def total_balance(self) -> Decimal:
        """Sum of available and locked demo balances."""
        return self.available_balance + self.locked_balance


class WalletTransaction(models.Model):
    """
    Append-only double-entry-style audit ledger for every balance-impacting wallet action.
    Guaranteed unique idempotency key prevents double crediting/debiting.
    """

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name="transactions",
        verbose_name="Wallet",
    )
    transaction_type = models.CharField(
        verbose_name="Transaction Type",
        max_length=32,
        choices=TRANSACTION_TYPE_CHOICES,
        db_index=True,
    )
    direction = models.CharField(
        verbose_name="Direction",
        max_length=10,
        choices=DIRECTION_CHOICES,
    )
    amount = models.DecimalField(
        verbose_name="Amount",
        max_digits=18,
        decimal_places=2,
    )
    balance_before = models.DecimalField(
        verbose_name="Available Balance Before",
        max_digits=18,
        decimal_places=2,
    )
    balance_after = models.DecimalField(
        verbose_name="Available Balance After",
        max_digits=18,
        decimal_places=2,
    )
    reference_type = models.CharField(
        verbose_name="Reference Type",
        max_length=64,
        blank=True,
        help_text="Entity type e.g. RewardPosition, DailyReward, Withdrawal.",
    )
    reference_id = models.CharField(
        verbose_name="Reference ID",
        max_length=64,
        blank=True,
        help_text="Primary key of referenced object.",
    )
    description = models.CharField(
        verbose_name="Description",
        max_length=255,
        help_text="Clear explanation, always prefixed with [DEMO].",
    )
    idempotency_key = models.CharField(
        verbose_name="Idempotency Key",
        max_length=128,
        unique=True,
        db_index=True,
        help_text="Guaranteed unique identifier preventing duplicate transaction processing.",
    )
    created_at = models.DateTimeField(
        verbose_name="Created At",
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        verbose_name = "Wallet Transaction"
        verbose_name_plural = "Wallet Transactions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["wallet", "created_at"], name="idx_tx_wallet_created"),
            models.Index(fields=["transaction_type"], name="idx_tx_type"),
            models.Index(fields=["idempotency_key"], name="idx_tx_idempotency"),
        ]

    def __str__(self):
        sign = "+" if self.direction == "CREDIT" else "-"
        return f"{self.transaction_type} {sign}{self.amount} {self.wallet.currency} ({self.idempotency_key})"
