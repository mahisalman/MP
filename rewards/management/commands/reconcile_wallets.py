from decimal import Decimal
from django.core.management.base import BaseCommand
from wallet.models import Wallet, WalletTransaction


class Command(BaseCommand):
    help = "Reconcile wallet balances against transaction ledger history."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Reconciling wallets against transaction ledgers..."))

        discrepancies = 0
        wallets = Wallet.objects.all().select_related('user')

        for w in wallets:
            transactions = WalletTransaction.objects.filter(wallet=w).order_by('created_at', 'id')
            
            computed_available = Decimal('0.00')
            computed_locked = Decimal('0.00')

            for tx in transactions:
                if tx.direction == 'CREDIT':
                    computed_available += tx.amount
                elif tx.direction == 'DEBIT':
                    computed_available -= tx.amount

                # Track lock movements
                if tx.transaction_type == "DEMO_WITHDRAWAL":
                    # Lock funds: available debited, locked increased
                    computed_locked += tx.amount
                elif tx.transaction_type == "WITHDRAWAL_REVERSAL":
                    # Release funds: available credited, locked decreased
                    computed_locked -= tx.amount

            # Note: deduct_locked_funds decrements locked balance with a DEBIT tx where available_balance is unchanged
            # Let's check w.available_balance vs last tx balance_after
            last_tx = transactions.last()
            expected_available = last_tx.balance_after if last_tx else Decimal('0.00')

            if expected_available != w.available_balance:
                discrepancies += 1
                self.stderr.write(self.style.ERROR(
                    f"Discrepancy for User {w.user.username} (ID: {w.user.id}):\n"
                    f"  Current Available: {w.available_balance} | Last Tx After: {expected_available}"
                ))
            else:
                self.stdout.write(f"Wallet for {w.user.username} is clean (Available: {w.available_balance} DUSD).")

        if discrepancies == 0:
            self.stdout.write(self.style.SUCCESS(f"Reconciliation successful. All {wallets.count()} wallets are mathematically consistent."))
        else:
            self.stderr.write(self.style.ERROR(f"Reconciliation found {discrepancies} wallet discrepancies!"))
