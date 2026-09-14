from decimal import Decimal
import logging
from datetime import date, timedelta
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ValidationError

from .models import RewardPlan, RewardPosition, DailyReward
from wallet.services import debit_wallet, credit_wallet, get_or_create_wallet
from audit.services import log_audit

logger = logging.getLogger('rewards')


def get_business_date():
    """
    Returns the current business date for reward calculation.
    If SIMULATION_MODE is enabled and a date is configured, returns that date;
    otherwise returns the current system UTC/local date.
    """
    sim_date_str = getattr(settings, 'SIMULATION_DATE', None)
    if getattr(settings, 'SIMULATION_MODE', False) and sim_date_str:
        try:
            return date.fromisoformat(sim_date_str)
        except (ValueError, TypeError):
            pass
    return timezone.now().date()


def create_demo_position(user, plan, demo_amount, idempotency_key=None):
    """
    Debits demo wallet and creates a new RewardPosition.
    Enforces min/max rules, active positions limit, and triggers referral rewards.
    """
    demo_amount = Decimal(str(demo_amount)).quantize(Decimal('0.01'))
    
    if demo_amount < plan.minimum_demo_amount or demo_amount > plan.maximum_demo_amount:
        raise ValidationError(f"Amount must be between {plan.minimum_demo_amount} and {plan.maximum_demo_amount} DUSD.")
    
    # Check max active positions per user
    max_positions = getattr(settings, 'MAX_ACTIVE_POSITIONS_PER_USER', 50)
    active_count = RewardPosition.objects.filter(user=user, status='ACTIVE').count()
    if active_count >= max_positions:
        raise ValidationError(f"Maximum active demo positions limit ({max_positions}) reached.")

    wallet = get_or_create_wallet(user)

    with transaction.atomic():
        # Debit wallet
        debit_desc = f"[DEMO] Allocate position in {plan.name} ({demo_amount} DUSD)"
        debit_idem = idempotency_key or f"pos-alloc-{user.id}-{timezone.now().timestamp()}"
        
        debit_tx = debit_wallet(
            wallet=wallet,
            amount=demo_amount,
            transaction_type="DEMO_POSITION_ALLOCATION",
            description=debit_desc,
            reference_type="RewardPlan",
            reference_id=str(plan.id),
            idempotency_key=debit_idem
        )
        
        # Calculate daily reward amount and total reward limit
        # Non-compounding: daily_amount = demo_amount * daily_rate
        daily_reward_amount = (demo_amount * plan.daily_rate).quantize(Decimal('0.01'))
        total_reward_limit = (daily_reward_amount * plan.duration_days).quantize(Decimal('0.01'))
        
        start_date = get_business_date()
        end_date = start_date + timedelta(days=plan.duration_days)
        
        position = RewardPosition.objects.create(
            user=user,
            reward_plan=plan,
            demo_amount=demo_amount,
            daily_rate=plan.daily_rate,
            duration_days=plan.duration_days,
            start_date=start_date,
            end_date=end_date,
            total_reward_limit=total_reward_limit,
            status='ACTIVE'
        )
        
        log_audit(
            actor=user,
            action='POSITION_ALLOCATED',
            resource_type='RewardPosition',
            resource_id=str(position.id),
            details={
                'plan': plan.name,
                'demo_amount': str(demo_amount),
                'daily_rate': str(plan.daily_rate),
                'duration_days': plan.duration_days,
                'total_reward_limit': str(total_reward_limit),
            }
        )
        
        # Trigger referral rewards
        try:
            from referrals.services import process_referral_rewards
            process_referral_rewards(position)
        except Exception as e:
            logger.error(f"Error processing referral rewards for position {position.id}: {e}")

        logger.info(f"[DEMO] Created position {position.id} for user {user.username}: {demo_amount} DUSD")
        return position


def process_daily_rewards_for_date(target_date=None):
    """
    Processes daily rewards for all active positions for the given target date.
    Idempotent: unique constraint on [position, reward_date] guarantees no double crediting.
    Updates position reward totals, and marks position COMPLETED if reached.
    Returns dict with summary stats.
    """
    if target_date is None:
        target_date = get_business_date()

    logger.info(f"[DEMO] Processing daily rewards for date: {target_date}")
    
    positions = RewardPosition.objects.filter(
        status='ACTIVE',
        start_date__lte=target_date,
        end_date__gte=target_date
    ).select_related('user', 'reward_plan')
    
    processed_count = 0
    skipped_count = 0
    completed_count = 0
    total_distributed = Decimal('0.00')

    for pos in positions:
        # Check if already rewarded for this date
        if DailyReward.objects.filter(position=pos, reward_date=target_date).exists():
            skipped_count += 1
            continue

        with transaction.atomic():
            # Lock position row
            locked_pos = RewardPosition.objects.select_for_update().get(id=pos.id)
            if locked_pos.status != 'ACTIVE':
                skipped_count += 1
                continue

            if DailyReward.objects.filter(position=locked_pos, reward_date=target_date).exists():
                skipped_count += 1
                continue

            # Deterministic reward amount
            reward_amt = locked_pos.daily_reward_amount
            
            # Ensure we do not exceed total_reward_limit
            remaining_cap = locked_pos.total_reward_limit - locked_pos.reward_earned
            if reward_amt > remaining_cap:
                reward_amt = remaining_cap

            if reward_amt <= Decimal('0.00'):
                locked_pos.status = 'COMPLETED'
                locked_pos.completed_at = timezone.now()
                locked_pos.save(update_fields=['status', 'completed_at'])
                completed_count += 1
                continue

            idem_key = f"daily-reward-pos-{locked_pos.id}-date-{target_date.isoformat()}"
            desc = f"[DEMO] Daily reward for position #{locked_pos.id} ({target_date.isoformat()})"
            wallet = get_or_create_wallet(locked_pos.user)

            # Credit wallet
            tx = credit_wallet(
                wallet=wallet,
                amount=reward_amt,
                transaction_type="DEMO_REWARD",
                description=desc,
                reference_type="RewardPosition",
                reference_id=str(locked_pos.id),
                idempotency_key=idem_key
            )
            
            # Record DailyReward
            DailyReward.objects.create(
                position=locked_pos,
                user=locked_pos.user,
                reward_date=target_date,
                calculation_amount=locked_pos.demo_amount,
                reward_rate=locked_pos.daily_rate,
                reward_amount=reward_amt,
                status='PROCESSED',
                ledger_transaction=tx
            )
            
            locked_pos.reward_earned += reward_amt
            locked_pos.last_reward_date = target_date
            
            # Check if duration completed or cap reached
            if locked_pos.days_completed >= locked_pos.duration_days or locked_pos.reward_earned >= locked_pos.total_reward_limit:
                locked_pos.status = 'COMPLETED'
                locked_pos.completed_at = timezone.now()
                completed_count += 1
                
            locked_pos.save(update_fields=['reward_earned', 'last_reward_date', 'status', 'completed_at'])
            
            processed_count += 1
            total_distributed += reward_amt

    summary = {
        'target_date': target_date.isoformat(),
        'processed_count': processed_count,
        'skipped_count': skipped_count,
        'completed_count': completed_count,
        'total_distributed': str(total_distributed)
    }
    logger.info(f"[DEMO] Daily rewards summary: {summary}")
    return summary
