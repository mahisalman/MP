from decimal import Decimal
import logging
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

from .models import Withdrawal
from wallet.services import lock_wallet_funds, release_wallet_funds, deduct_locked_funds, get_or_create_wallet
from audit.services import log_audit

logger = logging.getLogger('withdrawals')


def request_demo_withdrawal(user, amount, method, account_name, account_identifier, admin_note=""):
    """
    Submits a simulated withdrawal request.
    Atomically locks the requested amount in user's demo wallet.
    """
    amount = Decimal(str(amount)).quantize(Decimal('0.01'))
    if amount <= Decimal('0.00'):
        raise ValidationError("Demo withdrawal amount must be greater than zero.")
        
    wallet = get_or_create_wallet(user)

    with transaction.atomic():
        idem_key = f"wd-lock-{user.id}-{int(timezone.now().timestamp()*1000)}"
        desc = f"[DEMO] Lock funds for simulated withdrawal #{idem_key}"
        
        # Lock funds in wallet
        lock_tx = lock_wallet_funds(
            wallet=wallet,
            amount=amount,
            transaction_type="DEMO_WITHDRAWAL",
            description=desc,
            reference_type="User",
            reference_id=str(user.id),
            idempotency_key=idem_key
        )
        
        withdrawal = Withdrawal.objects.create(
            user=user,
            wallet=wallet,
            amount=amount,
            fee=Decimal('0.00'),
            net_amount=amount,
            method=method,
            account_name=account_name,
            account_identifier=account_identifier,
            status='PENDING',
            admin_note=admin_note
        )
        
        log_audit(
            actor=user,
            action='WITHDRAWAL_REQUESTED',
            resource_type='Withdrawal',
            resource_id=str(withdrawal.id),
            details={
                'amount': str(amount),
                'method': method,
                'account_name': account_name,
                'account_identifier': account_identifier
            }
        )
        logger.info(f"[DEMO] Withdrawal request #{withdrawal.id} created for {user.username}: {amount} DUSD")
        return withdrawal


def approve_demo_withdrawal(withdrawal, admin_user):
    """
    Moves a pending simulated withdrawal to APPROVED status.
    """
    with transaction.atomic():
        locked_wd = Withdrawal.objects.select_for_update().get(id=withdrawal.id)
        if locked_wd.status != 'PENDING':
            raise ValidationError(f"Withdrawal #{locked_wd.id} cannot be approved from status {locked_wd.status}")
            
        locked_wd.status = 'APPROVED'
        locked_wd.processed_by = admin_user
        locked_wd.approved_at = timezone.now()
        locked_wd.save(update_fields=['status', 'processed_by', 'approved_at'])
        
        log_audit(
            actor=admin_user,
            action='WITHDRAWAL_APPROVED',
            resource_type='Withdrawal',
            resource_id=str(locked_wd.id),
            details={'amount': str(locked_wd.amount)}
        )
        logger.info(f"[DEMO] Withdrawal #{locked_wd.id} approved by {admin_user.username}")
        return locked_wd


def reject_demo_withdrawal(withdrawal, admin_user, admin_note=""):
    """
    Rejects a pending or approved simulated withdrawal and releases locked funds back to user.
    """
    with transaction.atomic():
        locked_wd = Withdrawal.objects.select_for_update().get(id=withdrawal.id)
        if locked_wd.status not in ['PENDING', 'APPROVED']:
            raise ValidationError(f"Withdrawal #{locked_wd.id} cannot be rejected from status {locked_wd.status}")
            
        idem_key = f"wd-reject-rel-{locked_wd.id}"
        desc = f"[DEMO] Reversal of locked funds for rejected withdrawal #{locked_wd.id}"
        
        release_wallet_funds(
            wallet=locked_wd.wallet,
            amount=locked_wd.amount,
            transaction_type="WITHDRAWAL_REVERSAL",
            description=desc,
            reference_type="Withdrawal",
            reference_id=str(locked_wd.id),
            idempotency_key=idem_key
        )
        
        locked_wd.status = 'REJECTED'
        locked_wd.processed_by = admin_user
        locked_wd.rejected_at = timezone.now()
        locked_wd.admin_note = admin_note
        locked_wd.save(update_fields=['status', 'processed_by', 'rejected_at', 'admin_note'])
        
        log_audit(
            actor=admin_user,
            action='WITHDRAWAL_REJECTED',
            resource_type='Withdrawal',
            resource_id=str(locked_wd.id),
            details={'amount': str(locked_wd.amount), 'admin_note': admin_note}
        )
        logger.info(f"[DEMO] Withdrawal #{locked_wd.id} rejected by {admin_user.username}. Funds released.")
        return locked_wd


def complete_demo_withdrawal(withdrawal, admin_user, admin_note=""):
    """
    Marks a withdrawal COMPLETED and permanently deducts the locked funds from the wallet.
    """
    with transaction.atomic():
        locked_wd = Withdrawal.objects.select_for_update().get(id=withdrawal.id)
        if locked_wd.status not in ['PENDING', 'APPROVED']:
            raise ValidationError(f"Withdrawal #{locked_wd.id} cannot be completed from status {locked_wd.status}")
            
        idem_key = f"wd-comp-{locked_wd.id}"
        desc = f"[DEMO] Simulated withdrawal payout #{locked_wd.id} completed"
        
        deduct_locked_funds(
            wallet=locked_wd.wallet,
            amount=locked_wd.amount,
            transaction_type="DEMO_WITHDRAWAL",
            description=desc,
            reference_type="Withdrawal",
            reference_id=str(locked_wd.id),
            idempotency_key=idem_key
        )
        
        locked_wd.status = 'COMPLETED'
        locked_wd.processed_by = admin_user
        locked_wd.completed_at = timezone.now()
        if admin_note:
            locked_wd.admin_note = admin_note
        locked_wd.save(update_fields=['status', 'processed_by', 'completed_at', 'admin_note'])
        
        log_audit(
            actor=admin_user,
            action='WITHDRAWAL_COMPLETED',
            resource_type='Withdrawal',
            resource_id=str(locked_wd.id),
            details={'amount': str(locked_wd.amount)}
        )
        logger.info(f"[DEMO] Withdrawal #{locked_wd.id} marked completed by {admin_user.username}")
        return locked_wd
