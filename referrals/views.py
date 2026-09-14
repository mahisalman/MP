from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from decimal import Decimal
from .models import Referral, ReferralReward


@login_required
def referrals_view(request):
    user = request.user
    
    level_1_refs = Referral.objects.filter(referrer=user, level=1).select_related('referred_user')
    level_2_refs = Referral.objects.filter(referrer=user, level=2).select_related('referred_user')

    rewards = ReferralReward.objects.filter(referrer=user).order_by('-created_at')
    total_earned = sum((r.demo_amount for r in rewards), Decimal('0.00'))

    # Build referral full URL
    ref_url = request.build_absolute_uri(f"/register/?ref={user.referral_code}")

    return render(request, 'referrals/network.html', {
        'level_1_refs': level_1_refs,
        'level_2_refs': level_2_refs,
        'rewards': rewards[:20],
        'total_earned': total_earned,
        'ref_url': ref_url,
    })
