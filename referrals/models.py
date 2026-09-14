"""
Models for the referrals application.

Manages direct sponsor relationships, downline tracking, and simulated multi-level
referral rewards triggered upon qualifying demo position allocations.
"""

from decimal import Decimal
from django.conf import settings
from django.db import models


class ReferralPlan(models.Model):
    """
    Configurable referral reward rates for demo simulation.
    Level 1: 5%, Level 2: 2%.
    """

    name = models.CharField(max_length=100, default="Standard 2-Level Demo Plan")
    level_1_rate = models.DecimalField(
        verbose_name="Level 1 Rate",
        max_digits=6,
        decimal_places=4,
        default=Decimal("0.0500"),
        help_text="Direct sponsor reward percentage (e.g. 0.0500 = 5.00%).",
    )
    level_2_rate = models.DecimalField(
        verbose_name="Level 2 Rate",
        max_digits=6,
        decimal_places=4,
        default=Decimal("0.0200"),
        help_text="Second-level sponsor reward percentage (e.g. 0.0200 = 2.00%).",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Referral Plan"
        verbose_name_plural = "Referral Plans"

    def __str__(self):
        return f"{self.name} (L1: {self.level_1_rate*100:.1f}%, L2: {self.level_2_rate*100:.1f}%)"


class Referral(models.Model):
    """
    Direct sponsor relationship linking referred user to referrer.
    """

    referrer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="referrals_made",
        verbose_name="Sponsor",
    )
    referred_user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="referral_received",
        verbose_name="Referred User",
    )
    referral_code = models.CharField(max_length=12)
    level = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, default="ACTIVE")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Referral Relationship"
        verbose_name_plural = "Referral Relationships"
        indexes = [
            models.Index(fields=["referrer"], name="idx_ref_referrer"),
        ]

    def __str__(self):
        return f"{self.referrer.email} -> {self.referred_user.email}"


class ReferralReward(models.Model):
    """
    Virtual reward generated when a downline member allocates a demo position.
    """

    referral = models.ForeignKey(
        Referral,
        on_delete=models.CASCADE,
        related_name="rewards",
    )
    source_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="referral_rewards_generated",
        verbose_name="Source User",
    )
    beneficiary_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="referral_rewards_received",
        verbose_name="Beneficiary User",
    )
    source_position = models.ForeignKey(
        "rewards.RewardPosition",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="referral_rewards",
    )
    level = models.PositiveIntegerField(verbose_name="Referral Level (1 or 2)")
    rate = models.DecimalField(max_digits=6, decimal_places=4)
    base_amount = models.DecimalField(max_digits=18, decimal_places=2)
    reward_amount = models.DecimalField(max_digits=18, decimal_places=2)
    ledger_transaction = models.ForeignKey(
        "wallet.WalletTransaction",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="referral_reward_entries",
    )
    status = models.CharField(max_length=20, default="PROCESSED")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Demo Referral Reward"
        verbose_name_plural = "Demo Referral Rewards"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["beneficiary_user", "created_at"], name="idx_ref_reward_user"),
        ]

    def __str__(self):
        return f"Level {self.level} Reward ({self.reward_amount} DUSD) to {self.beneficiary_user.email}"
