from decimal import Decimal
import logging
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model

from .models import ReferralPlan, Referral, ReferralReward
from wallet.services import credit_wallet, get_or_create_wallet
from audit.services import log_audit

User = get_user_model()
logger = logging.getLogger('referrals')


def link_referral(user, referral_code):
    """
    Links a newly registered user to their sponsor using the sponsor's referral code.
    Prevents self-referral and cyclic references.
    """
    if not referral_code:
        return None
        
    referral_code = referral_code.strip().upper()
    try:
        sponsor = User.objects.get(referral_code=referral_code)
    except User.DoesNotExist:
        logger.warning(f"Invalid referral code provided: {referral_code}")
        return None
        
    if sponsor == user:
        logger.warning(f"User {user.username} tried to self-refer with code {referral_code}")
        return None

    # Check for direct cycle
    if sponsor.referred_by == user:
        logger.warning(f"Cyclic referral detected between {user.username} and {sponsor.username}")
        return None

    user.referred_by = sponsor
    user.save(update_fields=['referred_by'])

    # Record direct referral relationship
    rel, _ = Referral.objects.get_or_create(
        referred_user=user,
        defaults={
            'referrer': sponsor,
            'referral_code': referral_code,
            'level': 1,
            'status': 'ACTIVE'
        }
    )

    log_audit(
        actor=user,
        action='REFERRAL_LINKED',
        resource_type='User',
        resource_id=str(user.id),
        details={'sponsor_id': sponsor.id, 'sponsor_username': sponsor.username, 'code': referral_code}
    )
    logger.info(f"User {user.username} successfully linked to sponsor {sponsor.username}")
    return sponsor


def process_referral_rewards(position):
    """
    Distributes simulated 2-level referral rewards when a user allocates a demo position.
    Level 1: 5% (0.0500)
    Level 2: 2% (0.0200)
    """
    buyer = position.user
    if not buyer.referred_by:
        logger.info(f"User {buyer.username} has no sponsor. No referral rewards distributed.")
        return []

    # Get active referral plan or fallback
    plan = ReferralPlan.objects.filter(is_active=True).first()
    l1_rate = plan.level_1_rate if plan else Decimal('0.0500')
    l2_rate = plan.level_2_rate if plan else Decimal('0.0200')

    distributed_rewards = []
    
    # --- Level 1 Sponsor ---
    sponsor_l1 = buyer.referred_by
    l1_reward_amount = (position.demo_amount * l1_rate).quantize(Decimal('0.01'))
    
    # Get or create referral relationship for buyer and sponsor_l1
    ref_obj, _ = Referral.objects.get_or_create(
        referred_user=buyer,
        defaults={
            'referrer': sponsor_l1,
            'referral_code': sponsor_l1.referral_code,
            'level': 1,
            'status': 'ACTIVE'
        }
    )

    if l1_reward_amount > Decimal('0.00'):
        with transaction.atomic():
            l1_idem = f"ref-reward-pos-{position.id}-lvl-1-{sponsor_l1.id}"
            desc = f"[DEMO] Level 1 referral reward from {buyer.username}'s position #{position.id} ({l1_rate*100:.1f}%)"
            wallet_l1 = get_or_create_wallet(sponsor_l1)

            tx_l1 = credit_wallet(
                wallet=wallet_l1,
                amount=l1_reward_amount,
                transaction_type="REFERRAL_REWARD",
                description=desc,
                reference_type="RewardPosition",
                reference_id=str(position.id),
                idempotency_key=l1_idem
            )
            
            reward_obj = ReferralReward.objects.create(
                referral=ref_obj,
                source_user=buyer,
                beneficiary_user=sponsor_l1,
                source_position=position,
                level=1,
                rate=l1_rate,
                base_amount=position.demo_amount,
                reward_amount=l1_reward_amount,
                ledger_transaction=tx_l1,
                status='PROCESSED'
            )
            distributed_rewards.append(reward_obj)
            logger.info(f"[DEMO] Credited L1 referral reward {l1_reward_amount} DUSD to {sponsor_l1.username}")

    # --- Level 2 Sponsor ---
    sponsor_l2 = sponsor_l1.referred_by
    if sponsor_l2 and sponsor_l2 != buyer:
        l2_reward_amount = (position.demo_amount * l2_rate).quantize(Decimal('0.01'))
        if l2_reward_amount > Decimal('0.00'):
            with transaction.atomic():
                l2_idem = f"ref-reward-pos-{position.id}-lvl-2-{sponsor_l2.id}"
                desc = f"[DEMO] Level 2 referral reward from {buyer.username}'s position #{position.id} ({l2_rate*100:.1f}%)"
                wallet_l2 = get_or_create_wallet(sponsor_l2)

                tx_l2 = credit_wallet(
                    wallet=wallet_l2,
                    amount=l2_reward_amount,
                    transaction_type="REFERRAL_REWARD",
                    description=desc,
                    reference_type="RewardPosition",
                    reference_id=str(position.id),
                    idempotency_key=l2_idem
                )
                
                reward_obj = ReferralReward.objects.create(
                    referral=ref_obj,
                    source_user=buyer,
                    beneficiary_user=sponsor_l2,
                    source_position=position,
                    level=2,
                    rate=l2_rate,
                    base_amount=position.demo_amount,
                    reward_amount=l2_reward_amount,
                    ledger_transaction=tx_l2,
                    status='PROCESSED'
                )
                distributed_rewards.append(reward_obj)
                logger.info(f"[DEMO] Credited L2 referral reward {l2_reward_amount} DUSD to {sponsor_l2.username}")

    return distributed_rewards
