from decimal import Decimal
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum

from wallet.models import Wallet, WalletTransaction
from wallet.services import get_or_create_wallet
from rewards.models import RewardPosition, DailyReward
from rewards.services import get_business_date, process_daily_rewards_for_date
from withdrawals.models import Withdrawal
from withdrawals.services import approve_demo_withdrawal, reject_demo_withdrawal, complete_demo_withdrawal
from audit.models import AuditLog


@login_required
def dashboard_view(request):
    user = request.user
    wallet = get_or_create_wallet(user)
    
    positions = RewardPosition.objects.filter(user=user).order_by('-created_at')
    active_positions_count = positions.filter(status='ACTIVE').count()
    
    # Calculate daily simulated earnings estimate
    active_positions = positions.filter(status='ACTIVE')
    estimated_daily_yield = sum((p.daily_reward_amount for p in active_positions), Decimal('0.00'))
    
    recent_transactions = WalletTransaction.objects.filter(wallet=wallet).order_by('-created_at')[:5]
    recent_rewards = DailyReward.objects.filter(user=user).order_by('-reward_date')[:5]
    
    ref_url = request.build_absolute_uri(f"/register/?ref={user.referral_code}")
    
    return render(request, 'dashboard/home.html', {
        'wallet': wallet,
        'active_positions_count': active_positions_count,
        'estimated_daily_yield': estimated_daily_yield,
        'recent_transactions': recent_transactions,
        'recent_rewards': recent_rewards,
        'ref_url': ref_url,
        'business_date': get_business_date(),
    })


@user_passes_test(lambda u: u.is_staff)
def admin_simulation_control_view(request):
    """
    Control panel for staff/administrators to trigger daily reward simulations,
    advance simulation dates, and manage pending simulated withdrawals.
    """
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'run_daily_rewards':
            result = process_daily_rewards_for_date()
            messages.success(
                request,
                f"Simulated rewards processed for {result['target_date']}: "
                f"{result['processed_count']} positions credited ({result['total_distributed']} DUSD), "
                f"{result['skipped_count']} skipped, {result['completed_count']} completed."
            )
            return redirect('dashboard:admin_sim_control')
            
        elif action == 'approve_wd':
            wd_id = request.POST.get('withdrawal_id')
            wd = Withdrawal.objects.get(id=wd_id)
            approve_demo_withdrawal(wd, request.user)
            messages.success(request, f"Simulated withdrawal #{wd.id} approved.")
            return redirect('dashboard:admin_sim_control')

        elif action == 'reject_wd':
            wd_id = request.POST.get('withdrawal_id')
            reason = request.POST.get('reason', 'Rejected via admin simulation panel')
            wd = Withdrawal.objects.get(id=wd_id)
            reject_demo_withdrawal(wd, request.user, reason)
            messages.warning(request, f"Simulated withdrawal #{wd.id} rejected. Funds unlocked back to user balance.")
            return redirect('dashboard:admin_sim_control')

        elif action == 'complete_wd':
            wd_id = request.POST.get('withdrawal_id')
            wd = Withdrawal.objects.get(id=wd_id)
            complete_demo_withdrawal(wd, request.user)
            messages.success(request, f"Simulated withdrawal #{wd.id} marked completed. Funds permanently deducted.")
            return redirect('dashboard:admin_sim_control')

    pending_withdrawals = Withdrawal.objects.filter(status__in=['PENDING', 'APPROVED']).order_by('-requested_at')
    total_sim_deposits = Wallet.objects.aggregate(total=Sum('lifetime_credited'))['total'] or Decimal('0.00')
    total_sim_rewards = DailyReward.objects.aggregate(total=Sum('reward_amount'))['total'] or Decimal('0.00')
    total_sim_active_positions = RewardPosition.objects.filter(status='ACTIVE').count()
    recent_audit_logs = AuditLog.objects.order_by('-created_at')[:15]

    return render(request, 'dashboard/admin_control.html', {
        'pending_withdrawals': pending_withdrawals,
        'total_sim_deposits': total_sim_deposits,
        'total_sim_rewards': total_sim_rewards,
        'total_sim_active_positions': total_sim_active_positions,
        'recent_audit_logs': recent_audit_logs,
        'business_date': get_business_date(),
    })
