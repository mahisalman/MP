from decimal import Decimal
from django.core.management.base import BaseCommand
from rewards.models import RewardPosition, DailyReward


class Command(BaseCommand):
    help = "Reconcile daily reward records against position totals."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Reconciling daily rewards against positions..."))

        discrepancies = 0
        positions = RewardPosition.objects.all().select_related('user', 'reward_plan')

        for pos in positions:
            rewards = DailyReward.objects.filter(position=pos, status='PROCESSED')
            total_credited = sum((r.reward_amount for r in rewards), Decimal('0.00'))
            count_days = rewards.count()

            issues = []
            if total_credited != pos.reward_earned:
                issues.append(f"Credited sum {total_credited} != recorded {pos.reward_earned}")
            if count_days != pos.days_completed:
                issues.append(f"Reward count {count_days} != days completed {pos.days_completed}")
            if pos.reward_earned > pos.total_reward_limit:
                issues.append(f"Total credited {pos.reward_earned} exceeds limit {pos.total_reward_limit}")

            if issues:
                discrepancies += 1
                self.stderr.write(self.style.ERROR(
                    f"Discrepancy for Position #{pos.id} (User: {pos.user.username}):\n  " + "\n  ".join(issues)
                ))
            else:
                self.stdout.write(f"Position #{pos.id} ({pos.user.username}): Clean ({pos.days_completed}/{pos.duration_days} days, {pos.reward_earned} DUSD).")

        if discrepancies == 0:
            self.stdout.write(self.style.SUCCESS(f"Reconciliation successful. All {positions.count()} positions are mathematically consistent."))
        else:
            self.stderr.write(self.style.ERROR(f"Found {discrepancies} position discrepancies!"))
