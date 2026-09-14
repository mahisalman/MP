from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from rewards.models import RewardPlan, RewardPosition
from referrals.models import ReferralPlan
from referrals.services import link_referral
from wallet.services import get_or_create_wallet, create_demo_deposit
from rewards.services import create_demo_position

User = get_user_model()


class Command(BaseCommand):
    help = "Seed demo data: default 2% 75-day plan, referral plan, test users, demo balances, and demo positions."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding simulated reward data..."))

        # 1. Reward Plan
        plan, created = RewardPlan.objects.get_or_create(
            name='Demo 2% / 75-Day Simulation',
            defaults={
                'daily_rate': Decimal('0.0200'),
                'duration_days': 75,
                'minimum_demo_amount': Decimal('10.00'),
                'maximum_demo_amount': Decimal('10000.00'),
                'is_active': True,
                'is_demo': True
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created RewardPlan: {plan.name}"))
        else:
            self.stdout.write(f"RewardPlan already exists: {plan.name}")

        # 2. Referral Plan
        ref_plan, r_created = ReferralPlan.objects.get_or_create(
            name='Standard 2-Level Demo Plan',
            defaults={
                'level_1_rate': Decimal('0.0500'),
                'level_2_rate': Decimal('0.0200'),
                'is_active': True
            }
        )
        if r_created:
            self.stdout.write(self.style.SUCCESS(f"Created ReferralPlan: {ref_plan.name}"))

        # 3. Create Demo Users (Alice, Bob, Charlie)
        alice, _ = User.objects.get_or_create(
            email='alice@demo.local',
            defaults={
                'username': 'alice_demo',
                'full_name': 'Alice Demo',
                'mobile_number': '+8801700000001',
                'is_email_verified': True,
                'is_active': True
            }
        )
        if not alice.has_usable_password():
            alice.set_password('DemoPass123!')
            alice.save()
            
        bob, _ = User.objects.get_or_create(
            email='bob@demo.local',
            defaults={
                'username': 'bob_demo',
                'full_name': 'Bob Demo',
                'mobile_number': '+8801700000002',
                'is_email_verified': True,
                'is_active': True
            }
        )
        if not bob.has_usable_password():
            bob.set_password('DemoPass123!')
            bob.save()
        if not bob.referred_by:
            link_referral(bob, alice.referral_code)

        charlie, _ = User.objects.get_or_create(
            email='charlie@demo.local',
            defaults={
                'username': 'charlie_demo',
                'full_name': 'Charlie Demo',
                'mobile_number': '+8801700000003',
                'is_email_verified': True,
                'is_active': True
            }
        )
        if not charlie.has_usable_password():
            charlie.set_password('DemoPass123!')
            charlie.save()
        if not charlie.referred_by:
            link_referral(charlie, bob.referral_code)

        # 4. Credit Demo Balances
        for u in [alice, bob, charlie]:
            w = get_or_create_wallet(u)
            if w.available_balance < Decimal('1000.00'):
                create_demo_deposit(u, Decimal('1000.00'))
                self.stdout.write(self.style.SUCCESS(f"Deposited 1000.00 DUSD to {u.username}"))

        # 5. Create sample position for Charlie if none exists
        if not RewardPosition.objects.filter(user=charlie).exists():
            pos = create_demo_position(charlie, plan, Decimal('100.00'))
            self.stdout.write(self.style.SUCCESS(
                f"Allocated demo position #{pos.id} for {charlie.username}: 100.00 DUSD (Daily: 2.00 DUSD, 75 days)"
            ))

        self.stdout.write(self.style.SUCCESS("Demo seeding completed successfully!"))
