from datetime import date
from django.core.management.base import BaseCommand
from rewards.services import process_daily_rewards_for_date


class Command(BaseCommand):
    help = "Process daily rewards for active demo positions for a specific date (or current business date)."

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Target business date in YYYY-MM-DD format (defaults to current business date)',
        )

    def handle(self, *args, **options):
        target_date_str = options.get('date')
        target_date = None
        if target_date_str:
            try:
                target_date = date.fromisoformat(target_date_str)
            except ValueError:
                self.stderr.write(self.style.ERROR(f"Invalid date format: {target_date_str}. Use YYYY-MM-DD."))
                return

        self.stdout.write(self.style.NOTICE(f"[DEMO] Running daily reward calculation for date: {target_date or 'today'}..."))
        result = process_daily_rewards_for_date(target_date)
        
        self.stdout.write(self.style.SUCCESS(
            f"Successfully processed daily rewards for {result['target_date']}:\n"
            f"  - Positions Credited: {result['processed_count']}\n"
            f"  - Positions Skipped (already credited or inactive): {result['skipped_count']}\n"
            f"  - Positions Completed: {result['completed_count']}\n"
            f"  - Total Distributed: {result['total_distributed']} DUSD"
        ))
