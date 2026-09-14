from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from rewards.models import RewardPlan, RewardPosition, DailyReward
from rewards.services import create_demo_position, process_daily_rewards_for_date
from referrals.models import ReferralPlan, Referral, ReferralReward
from referrals.services import link_referral
from wallet.services import get_or_create_wallet, create_demo_deposit
from withdrawals.models import Withdrawal
from withdrawals.services import (
    request_demo_withdrawal,
    approve_demo_withdrawal,
    reject_demo_withdrawal,
    complete_demo_withdrawal,
)

User = get_user_model()


class SimulationScenariosTestCase(TestCase):
    """
    Automated test suite verifying the 4 mandatory platform scenarios:
    1. Scenario 1: Exact 2% non-compounding daily calculation over multiple days with 150% cap.
    2. Scenario 2: Double-credit idempotency prevention on repeated execution for same date.
    3. Scenario 3: 2-Level simulated referral bonuses crediting correct percentages.
    4. Scenario 4: Simulated withdrawal lifecycle (Lock -> Reject -> Release, and Lock -> Complete).
    """

    def setUp(self):
        # Create standard reward plan: 2% for 75 days (150% cap)
        self.reward_plan = RewardPlan.objects.create(
            name="Demo 2% / 75-Day Plan",
            daily_rate=Decimal("0.0200"),
            duration_days=75,
            minimum_demo_amount=Decimal("10.00"),
            maximum_demo_amount=Decimal("10000.00"),
            is_active=True,
            is_demo=True,
        )

        # Create standard 2-level referral plan: L1 = 5%, L2 = 2%
        self.referral_plan = ReferralPlan.objects.create(
            name="Test Referral Plan",
            level_1_rate=Decimal("0.0500"),
            level_2_rate=Decimal("0.0200"),
            is_active=True,
        )

        # Create users
        self.alice = User.objects.create_user(
            email="alice@test.local",
            username="alice",
            full_name="Alice Test",
            mobile_number="+8801711111111",
            password="Password123!",
            is_email_verified=True,
            is_active=True,
        )
        self.bob = User.objects.create_user(
            email="bob@test.local",
            username="bob",
            full_name="Bob Test",
            mobile_number="+8801722222222",
            password="Password123!",
            is_email_verified=True,
            is_active=True,
        )
        self.charlie = User.objects.create_user(
            email="charlie@test.local",
            username="charlie",
            full_name="Charlie Test",
            mobile_number="+8801733333333",
            password="Password123!",
            is_email_verified=True,
            is_active=True,
        )

        # Link referrals: Alice -> Bob -> Charlie
        link_referral(self.bob, self.alice.referral_code)
        link_referral(self.charlie, self.bob.referral_code)

        # Deposit demo funds
        create_demo_deposit(self.alice, Decimal("1000.00"))
        create_demo_deposit(self.bob, Decimal("1000.00"))
        create_demo_deposit(self.charlie, Decimal("1000.00"))

    def test_scenario_1_deterministic_2_percent_daily_calculation(self):
        """
        Verify: 100 DUSD position yields exactly 2.00 DUSD per day (non-compounding).
        After 75 days, rewards cap at 150.00 DUSD and position marks COMPLETED.
        """
        position = create_demo_position(self.charlie, self.reward_plan, Decimal("100.00"))
        self.assertEqual(position.daily_reward_amount, Decimal("2.00"))
        self.assertEqual(position.total_reward_limit, Decimal("150.00"))

        start_date = position.start_date
        wallet_before = get_or_create_wallet(self.charlie).available_balance

        # Simulate 75 daily executions
        for day_offset in range(75):
            current_date = start_date + timedelta(days=day_offset)
            res = process_daily_rewards_for_date(current_date)
            self.assertEqual(res["processed_count"], 1)

        position.refresh_from_db()
        self.assertEqual(position.days_completed, 75)
        self.assertEqual(position.reward_earned, Decimal("150.00"))
        self.assertEqual(position.status, "COMPLETED")

        # Running 76th day must not credit any extra rewards
        day_76 = start_date + timedelta(days=75)
        res_76 = process_daily_rewards_for_date(day_76)
        self.assertEqual(res_76["processed_count"], 0)

        position.refresh_from_db()
        self.assertEqual(position.reward_earned, Decimal("150.00"))

        wallet_after = get_or_create_wallet(self.charlie).available_balance
        self.assertEqual(wallet_after, wallet_before + Decimal("150.00"))

    def test_scenario_2_double_credit_idempotency_prevention(self):
        """
        Verify: Calling process_daily_rewards multiple times on the same date
        never credits more than once.
        """
        position = create_demo_position(self.charlie, self.reward_plan, Decimal("100.00"))
        test_date = position.start_date

        res1 = process_daily_rewards_for_date(test_date)
        self.assertEqual(res1["processed_count"], 1)
        self.assertEqual(res1["skipped_count"], 0)

        # Run 2nd, 3rd time on the same date
        res2 = process_daily_rewards_for_date(test_date)
        self.assertEqual(res2["processed_count"], 0)
        self.assertEqual(res2["skipped_count"], 1)

        res3 = process_daily_rewards_for_date(test_date)
        self.assertEqual(res3["processed_count"], 0)
        self.assertEqual(res3["skipped_count"], 1)

        # Verify only 1 DailyReward row exists
        self.assertEqual(DailyReward.objects.filter(position=position).count(), 1)
        position.refresh_from_db()
        self.assertEqual(position.reward_earned, Decimal("2.00"))

    def test_scenario_3_two_level_simulated_referral_rewards(self):
        """
        Verify: When Charlie allocates 100 DUSD:
        - Bob (Level 1 sponsor) receives 5% = 5.00 DUSD
        - Alice (Level 2 sponsor) receives 2% = 2.00 DUSD
        """
        alice_wallet_before = get_or_create_wallet(self.alice).available_balance
        bob_wallet_before = get_or_create_wallet(self.bob).available_balance

        position = create_demo_position(self.charlie, self.reward_plan, Decimal("100.00"))

        alice_wallet_after = get_or_create_wallet(self.alice).available_balance
        bob_wallet_after = get_or_create_wallet(self.bob).available_balance

        self.assertEqual(bob_wallet_after, bob_wallet_before + Decimal("5.00"))
        self.assertEqual(alice_wallet_after, alice_wallet_before + Decimal("2.00"))

        # Verify ReferralReward records
        rewards = ReferralReward.objects.filter(source_position=position)
        self.assertEqual(rewards.count(), 2)

        l1_reward = rewards.get(level=1)
        self.assertEqual(l1_reward.beneficiary_user, self.bob)
        self.assertEqual(l1_reward.reward_amount, Decimal("5.00"))

        l2_reward = rewards.get(level=2)
        self.assertEqual(l2_reward.beneficiary_user, self.alice)
        self.assertEqual(l2_reward.reward_amount, Decimal("2.00"))

    def test_scenario_4_simulated_withdrawal_lifecycle(self):
        """
        Verify:
        Part A: Request 50 DUSD -> funds locked -> admin rejects -> funds released to available balance.
        Part B: Request 50 DUSD -> funds locked -> admin completes -> locked funds deducted permanently.
        """
        wallet = get_or_create_wallet(self.alice)
        initial_available = wallet.available_balance

        # Part A: Rejection flow
        wd_a = request_demo_withdrawal(
            user=self.alice,
            amount=Decimal("50.00"),
            method="DEMO_CRYPTO",
            account_name="Alice",
            account_identifier="0xDEMO123",
        )
        wallet.refresh_from_db()
        self.assertEqual(wallet.available_balance, initial_available - Decimal("50.00"))
        self.assertEqual(wallet.locked_balance, Decimal("50.00"))

        reject_demo_withdrawal(wd_a, admin_user=self.bob, admin_note="Test rejection")
        wallet.refresh_from_db()
        self.assertEqual(wallet.available_balance, initial_available)
        self.assertEqual(wallet.locked_balance, Decimal("0.00"))

        # Part B: Completion flow
        wd_b = request_demo_withdrawal(
            user=self.alice,
            amount=Decimal("50.00"),
            method="DEMO_MOBILE_WALLET",
            account_name="Alice",
            account_identifier="01711111111",
        )
        wallet.refresh_from_db()
        self.assertEqual(wallet.available_balance, initial_available - Decimal("50.00"))
        self.assertEqual(wallet.locked_balance, Decimal("50.00"))

        approve_demo_withdrawal(wd_b, admin_user=self.bob)
        complete_demo_withdrawal(wd_b, admin_user=self.bob)
        wallet.refresh_from_db()
        self.assertEqual(wallet.available_balance, initial_available - Decimal("50.00"))
        self.assertEqual(wallet.locked_balance, Decimal("0.00"))
        self.assertEqual(wallet.lifetime_debited, Decimal("50.00"))
