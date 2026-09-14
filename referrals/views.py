from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from decimal import Decimal
from .models import Referral, ReferralReward


@login_required
def referrals_view(request):
    user = request.user
    
    # Direct downlines (Level 1)
    level_1_users = list(user.direct_referrals.all().order_by('-date_joined'))
    
    # Indirect downlines (Level 2: users referred by Level 1 users)
    level_2_users = []
    if level_1_users:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        level_2_users = list(User.objects.filter(referred_by__in=level_1_users).select_related('referred_by').order_by('-date_joined'))

    rewards = ReferralReward.objects.filter(beneficiary_user=user).select_related('source_user').order_by('-created_at')
    total_earned = sum((r.reward_amount for r in rewards), Decimal('0.00'))

    # Build referral full URL
    ref_url = request.build_absolute_uri(f"/register/?ref={user.referral_code}")

    return render(request, 'referrals/network.html', {
        'level_1_users': level_1_users,
        'level_2_users': level_2_users,
        'rewards': rewards[:20],
        'total_earned': total_earned,
        'ref_url': ref_url,
    })
