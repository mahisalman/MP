from django.core.management.base import BaseCommand
from django.db import transaction
from django.conf import settings
from rewards.models import RewardPosition, DailyReward
from referrals.models import ReferralReward, Referral
from withdrawals.models import Withdrawal
from wallet.models import Wallet, WalletTransaction
from audit.models import AuditLog


class Command(BaseCommand):
    help = "Reset all simulated reward and transaction data (DEMO ENVIRONMENT ONLY)."

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm wiping demo transaction records',
        )

    def handle(self, *args, **options):
        if not getattr(settings, 'DEMO_MODE', False):
            self.stderr.write(self.style.ERROR("ABORTED: Cannot reset demo data when DEMO_MODE is False."))
            return

        if not options.get('confirm'):
            self.stdout.write(self.style.WARNING("To safely wipe simulation data, re-run with --confirm flag."))
            return

        self.stdout.write(self.style.WARNING("Wiping demo rewards, withdrawals, referral logs, and zeroing wallets..."))

        with transaction.atomic():
            DailyReward.objects.all().delete()
            ReferralReward.objects.all().delete()
            RewardPosition.objects.all().delete()
            Withdrawal.objects.all().delete()
            WalletTransaction.objects.all().delete()
            AuditLog.objects.all().delete()

            # Zero out wallets
            Wallet.objects.all().update(
                available_balance=0,
                locked_balance=0,
                lifetime_credited=0,
                lifetime_debited=0
            )

        self.stdout.write(self.style.SUCCESS("All simulation records have been cleanly wiped and demo balances reset to 0."))
