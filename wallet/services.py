"""
Centralized business logic services for virtual demo wallet operations.

Guarantees thread safety with database row locking (select_for_update),
atomic transactions, idempotency enforcement, and append-only ledger bookkeeping.
"""

import logging
import secrets
import time
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Wallet, WalletTransaction

logger = logging.getLogger("wallet")

ALLOWED_DEMO_DEPOSIT_AMOUNTS = [
    Decimal("10.00"),
    Decimal("50.00"),
    Decimal("100.00"),
    Decimal("500.00"),
    Decimal("1000.00"),
    Decimal("500.00"),
    Decimal("10000.00"),
]


def ensure_demo_prefix(description: str) -> str:
    """Guarantees that all transaction descriptions begin with [DEMO]."""
    clean_desc = description.strip()
    if not clean_desc.startswith("[DEMO]"):
        return f"[DEMO] {clean_desc}"
    return clean_desc


def get_or_create_wallet(user) -> Wallet:
    """Retrieves or initializes a demo wallet for the user."""
    wallet, _ = Wallet.objects.get_or_create(
        user=user,
        defaults={
            "currency": "DUSD",
            "available_balance": Decimal("0.00"),
            "locked_balance": Decimal("0.00"),
            "lifetime_credited": Decimal("0.00"),
            "lifetime_debited": Decimal("0.00"),
        },
    )
    return wallet


def credit_wallet(
    wallet: Wallet,
    amount: Decimal,
    transaction_type: str,
    description: str,
    reference_type: str = "",
    reference_id: str = "",
    idempotency_key: str = None,
) -> WalletTransaction:
    """
    Safely credits funds to the wallet available balance with row locking.
    Idempotent: returns existing transaction if idempotency_key is repeated.
    """
    if amount <= Decimal("0.00"):
        raise ValidationError("Credit amount must be greater than zero.")

    if not idempotency_key:
        idempotency_key = f"credit-{wallet.id}-{int(time.time()*1000)}-{secrets.token_hex(4)}"

    with transaction.atomic():
        # Check idempotency first
        existing_tx = WalletTransaction.objects.filter(idempotency_key=idempotency_key).first()
        if existing_tx:
            logger.info("Idempotent credit hit for key=%s; skipping credit.", idempotency_key)
            return existing_tx

        # Acquire exclusive row lock on wallet
        locked_wallet = Wallet.objects.select_for_update().get(id=wallet.id)

        balance_before = locked_wallet.available_balance
        balance_after = balance_before + amount

        locked_wallet.available_balance = balance_after
        locked_wallet.lifetime_credited += amount
        locked_wallet.save(update_fields=["available_balance", "lifetime_credited", "updated_at"])

        tx = WalletTransaction.objects.create(
            wallet=locked_wallet,
            transaction_type=transaction_type,
            direction="CREDIT",
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            reference_type=reference_type,
            reference_id=str(reference_id),
            description=ensure_demo_prefix(description),
            idempotency_key=idempotency_key,
        )

        logger.info(
            "Credited %s DUSD to wallet id=%s. Tx ID: %s. Idempotency: %s",
            amount,
            locked_wallet.id,
            tx.id,
            idempotency_key,
        )
        return tx


def debit_wallet(
    wallet: Wallet,
    amount: Decimal,
    transaction_type: str,
    description: str,
    reference_type: str = "",
    reference_id: str = "",
    idempotency_key: str = None,
) -> WalletTransaction:
    """
    Safely debits funds from the wallet available balance with row locking.
    Prevents negative balances.
    """
    if amount <= Decimal("0.00"):
        raise ValidationError("Debit amount must be greater than zero.")

    if not idempotency_key:
        idempotency_key = f"debit-{wallet.id}-{int(time.time()*1000)}-{secrets.token_hex(4)}"

    with transaction.atomic():
        existing_tx = WalletTransaction.objects.filter(idempotency_key=idempotency_key).first()
        if existing_tx:
            logger.info("Idempotent debit hit for key=%s; skipping debit.", idempotency_key)
            return existing_tx

        # Row lock
        locked_wallet = Wallet.objects.select_for_update().get(id=wallet.id)

        if locked_wallet.available_balance < amount:
            raise ValidationError(
                f"Insufficient demo balance. Available: {locked_wallet.available_balance} {locked_wallet.currency}, Required: {amount} {locked_wallet.currency}."
            )

        balance_before = locked_wallet.available_balance
        balance_after = balance_before - amount

        locked_wallet.available_balance = balance_after
        locked_wallet.lifetime_debited += amount
        locked_wallet.save(update_fields=["available_balance", "lifetime_debited", "updated_at"])

        tx = WalletTransaction.objects.create(
            wallet=locked_wallet,
            transaction_type=transaction_type,
            direction="DEBIT",
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            reference_type=reference_type,
            reference_id=str(reference_id),
            description=ensure_demo_prefix(description),
            idempotency_key=idempotency_key,
        )

        logger.info(
            "Debited %s DUSD from wallet id=%s. Tx ID: %s. Idempotency: %s",
            amount,
            locked_wallet.id,
            tx.id,
            idempotency_key,
        )
        return tx


def lock_wallet_funds(
    wallet: Wallet,
    amount: Decimal,
    transaction_type: str,
    description: str,
    reference_type: str = "",
    reference_id: str = "",
    idempotency_key: str = None,
) -> WalletTransaction:
    """
    Moves funds from available_balance to locked_balance (e.g. pending withdrawal).
    """
    if amount <= Decimal("0.00"):
        raise ValidationError("Amount to lock must be greater than zero.")

    if not idempotency_key:
        idempotency_key = f"lock-{wallet.id}-{int(time.time()*1000)}-{secrets.token_hex(4)}"

    with transaction.atomic():
        existing_tx = WalletTransaction.objects.filter(idempotency_key=idempotency_key).first()
        if existing_tx:
            return existing_tx

        locked_wallet = Wallet.objects.select_for_update().get(id=wallet.id)

        if locked_wallet.available_balance < amount:
            raise ValidationError(
                f"Insufficient available demo balance to lock. Available: {locked_wallet.available_balance} DUSD, Requested: {amount} DUSD."
            )

        balance_before = locked_wallet.available_balance
        balance_after = balance_before - amount

        locked_wallet.available_balance = balance_after
        locked_wallet.locked_balance += amount
        locked_wallet.save(update_fields=["available_balance", "locked_balance", "updated_at"])

        tx = WalletTransaction.objects.create(
            wallet=locked_wallet,
            transaction_type=transaction_type,
            direction="DEBIT",
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            reference_type=reference_type,
            reference_id=str(reference_id),
            description=ensure_demo_prefix(description),
            idempotency_key=idempotency_key,
        )
        return tx


def release_wallet_funds(
    wallet: Wallet,
    amount: Decimal,
    transaction_type: str,
    description: str,
    reference_type: str = "",
    reference_id: str = "",
    idempotency_key: str = None,
) -> WalletTransaction:
    """
    Releases locked funds back to available balance (e.g. when withdrawal is rejected).
    """
    if amount <= Decimal("0.00"):
        raise ValidationError("Amount to release must be greater than zero.")

    if not idempotency_key:
        idempotency_key = f"release-{wallet.id}-{int(time.time()*1000)}-{secrets.token_hex(4)}"

    with transaction.atomic():
        existing_tx = WalletTransaction.objects.filter(idempotency_key=idempotency_key).first()
        if existing_tx:
            return existing_tx

        locked_wallet = Wallet.objects.select_for_update().get(id=wallet.id)

        locked_amount = min(locked_wallet.locked_balance, amount)
        balance_before = locked_wallet.available_balance
        balance_after = balance_before + locked_amount

        locked_wallet.available_balance = balance_after
        locked_wallet.locked_balance -= locked_amount
        locked_wallet.save(update_fields=["available_balance", "locked_balance", "updated_at"])

        tx = WalletTransaction.objects.create(
            wallet=locked_wallet,
            transaction_type=transaction_type,
            direction="CREDIT",
            amount=locked_amount,
            balance_before=balance_before,
            balance_after=balance_after,
            reference_type=reference_type,
            reference_id=str(reference_id),
            description=ensure_demo_prefix(description),
            idempotency_key=idempotency_key,
        )
        return tx


def deduct_locked_funds(
    wallet: Wallet,
    amount: Decimal,
    transaction_type: str,
    description: str,
    reference_type: str = "",
    reference_id: str = "",
    idempotency_key: str = None,
) -> WalletTransaction:
    """
    Permanently deducts locked balance upon completed withdrawal.
    """
    if amount <= Decimal("0.00"):
        raise ValidationError("Amount to deduct must be greater than zero.")

    if not idempotency_key:
        idempotency_key = f"deduct-lock-{wallet.id}-{int(time.time()*1000)}-{secrets.token_hex(4)}"

    with transaction.atomic():
        existing_tx = WalletTransaction.objects.filter(idempotency_key=idempotency_key).first()
        if existing_tx:
            return existing_tx

        locked_wallet = Wallet.objects.select_for_update().get(id=wallet.id)

        locked_wallet.locked_balance = max(Decimal("0.00"), locked_wallet.locked_balance - amount)
        locked_wallet.lifetime_debited += amount
        locked_wallet.save(update_fields=["locked_balance", "lifetime_debited", "updated_at"])

        tx = WalletTransaction.objects.create(
            wallet=locked_wallet,
            transaction_type=transaction_type,
            direction="DEBIT",
            amount=amount,
            balance_before=locked_wallet.available_balance,
            balance_after=locked_wallet.available_balance,
            reference_type=reference_type,
            reference_id=str(reference_id),
            description=ensure_demo_prefix(description),
            idempotency_key=idempotency_key,
        )
        return tx


def create_demo_deposit(user, amount: Decimal) -> WalletTransaction:
    """
    Simulates adding demo credits to the user's demo wallet.
    Only permitted demo amounts are accepted.
    """
    amount = Decimal(str(amount))
    valid_amounts = [Decimal("10.00"), Decimal("50.00"), Decimal("100.00"), Decimal("500.00"), Decimal("1000.00"), Decimal("5000.00"), Decimal("10000.00")]
    if amount not in valid_amounts:
        raise ValidationError(f"Invalid demo amount. Choose from: {', '.join(str(a) for a in valid_amounts)} DUSD.")

    wallet = get_or_create_wallet(user)
    idempotency_key = f"demo-deposit-{user.id}-{int(time.time()*1000)}-{secrets.token_hex(4)}"

    return credit_wallet(
        wallet=wallet,
        amount=amount,
        transaction_type="DEMO_DEPOSIT",
        description=f"[DEMO] Self-service test credit deposit of {amount} DUSD",
        reference_type="User",
        reference_id=str(user.id),
        idempotency_key=idempotency_key,
    )
