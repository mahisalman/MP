"""
Models for the rewards application.

Defines RewardPlan, virtual RewardPosition (2% x 75-day deterministic simulation),
and append-only DailyReward tracking with strict database-level unique constraints.
"""

from decimal import Decimal
from django.conf import settings
from django.db import models


POSITION_STATUS_CHOICES = [
    ("PENDING", "Pending"),
    ("ACTIVE", "Active"),
    ("PAUSED", "Paused"),
    ("COMPLETED", "Completed"),
    ("CANCELLED", "Cancelled"),
    ("EXPIRED", "Expired"),
]

DAILY_REWARD_STATUS_CHOICES = [
    ("PENDING", "Pending"),
    ("PROCESSED", "Processed"),
    ("SKIPPED", "Skipped"),
    ("REVERSED", "Reversed"),
]


class RewardPlan(models.Model):
    """
    Configurable reward simulation plan.
    Default: Demo 2% / 75-Day Simulation (150% total return in virtual DUSD).
    """

    name = models.CharField(
        verbose_name="Plan Name",
        max_length=100,
        default="Demo 2% / 75-Day Simulation",
    )
    daily_rate = models.DecimalField(
        verbose_name="Daily Rate",
        max_digits=6,
        decimal_places=4,
        default=Decimal("0.0200"),
        help_text="Decimal rate (e.g. 0.0200 = 2.00% per day).",
    )
    duration_days = models.PositiveIntegerField(
        verbose_name="Duration (Days)",
        default=75,
        help_text="Total simulation days before position completes.",
    )
    minimum_demo_amount = models.DecimalField(
        verbose_name="Minimum Demo Amount",
        max_digits=18,
        decimal_places=2,
        default=Decimal("10.00"),
    )
    maximum_demo_amount = models.DecimalField(
        verbose_name="Maximum Demo Amount",
        max_digits=18,
        decimal_places=2,
        default=Decimal("10000.00"),
    )
    is_active = models.BooleanField(default=True)
    is_demo = models.BooleanField(
        default=True,
        help_text="Ensures this plan only executes in simulated demo mode.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Reward Plan"
        verbose_name_plural = "Reward Plans"

    def __str__(self):
        return f"{self.name} ({self.daily_rate * 100:.1f}% x {self.duration_days} Days)"


class RewardPosition(models.Model):
    """
    Simulated active reward position for a user.
    Calculates deterministic non-compounding daily rewards: original_demo_amount * daily_rate.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reward_positions",
        verbose_name="User",
    )
    reward_plan = models.ForeignKey(
        RewardPlan,
        on_delete=models.PROTECT,
        related_name="positions",
        verbose_name="Plan",
    )
    demo_amount = models.DecimalField(
        verbose_name="Allocated Demo Amount",
        max_digits=18,
        decimal_places=2,
        help_text="Initial virtual funds debited from user wallet.",
    )
    daily_rate = models.DecimalField(
        verbose_name="Applied Daily Rate",
        max_digits=6,
        decimal_places=4,
    )
    duration_days = models.PositiveIntegerField(
        verbose_name="Duration (Days)",
        default=75,
    )
    start_date = models.DateField(
        verbose_name="Start Date",
        db_index=True,
    )
    end_date = models.DateField(
        verbose_name="End Date",
        db_index=True,
    )
    total_reward_limit = models.DecimalField(
        verbose_name="Total Reward Limit",
        max_digits=18,
        decimal_places=2,
        help_text="Maximum lifetime rewards this position can produce (e.g. 150 DUSD for 100 DUSD at 2% x 75 days).",
    )
    reward_earned = models.DecimalField(
        verbose_name="Reward Earned",
        max_digits=18,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    last_reward_date = models.DateField(
        verbose_name="Last Reward Date",
        null=True,
        blank=True,
    )
    status = models.CharField(
        verbose_name="Status",
        max_length=20,
        choices=POSITION_STATUS_CHOICES,
        default="ACTIVE",
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Demo Reward Position"
        verbose_name_plural = "Demo Reward Positions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"], name="idx_pos_user_status"),
            models.Index(fields=["status", "start_date", "end_date"], name="idx_pos_active_dates"),
        ]

    def __str__(self):
        return f"Position #{self.id} - {self.demo_amount} DUSD ({self.status})"

    @property
    def daily_reward_amount(self) -> Decimal:
        """Deterministic non-compounding daily simulated reward."""
        return (self.demo_amount * self.daily_rate).quantize(Decimal("0.01"))

    @property
    def days_completed(self) -> int:
        """Count of processed daily rewards."""
        return self.daily_rewards.filter(status="PROCESSED").count()

    @property
    def days_remaining(self) -> int:
        """Remaining simulation reward days."""
        return max(0, self.duration_days - self.days_completed)

    @property
    def progress_percentage(self) -> int:
        """Percentage of total simulated reward earned so far."""
        if self.total_reward_limit <= Decimal("0.00"):
            return 100
        pct = (self.reward_earned / self.total_reward_limit) * Decimal("100")
        return min(100, max(0, int(pct)))


class DailyReward(models.Model):
    """
    Record of each processed daily simulated reward.
    Guaranteed unique per position per day to prevent duplicate payouts.
    """

    position = models.ForeignKey(
        RewardPosition,
        on_delete=models.CASCADE,
        related_name="daily_rewards",
        verbose_name="Position",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="daily_rewards",
        verbose_name="User",
    )
    reward_date = models.DateField(
        verbose_name="Reward Date",
        db_index=True,
    )
    calculation_amount = models.DecimalField(
        verbose_name="Base Amount",
        max_digits=18,
        decimal_places=2,
    )
    reward_rate = models.DecimalField(
        verbose_name="Reward Rate",
        max_digits=6,
        decimal_places=4,
    )
    reward_amount = models.DecimalField(
        verbose_name="Reward Credited",
        max_digits=18,
        decimal_places=2,
    )
    status = models.CharField(
        verbose_name="Status",
        max_length=20,
        choices=DAILY_REWARD_STATUS_CHOICES,
        default="PROCESSED",
    )
    ledger_transaction = models.ForeignKey(
        "wallet.WalletTransaction",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="daily_reward_entries",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Daily Demo Reward"
        verbose_name_plural = "Daily Demo Rewards"
        ordering = ["-reward_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["position", "reward_date"],
                name="unique_position_reward_date",
            )
        ]
        indexes = [
            models.Index(fields=["position", "reward_date"], name="idx_daily_pos_date"),
            models.Index(fields=["user", "reward_date"], name="idx_daily_user_date"),
        ]

    def __str__(self):
        return f"Reward {self.reward_amount} DUSD for Pos #{self.position_id} on {self.reward_date}"
