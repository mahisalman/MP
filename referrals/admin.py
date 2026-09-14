from django.contrib import admin
from .models import ReferralPlan, Referral, ReferralReward

@admin.register(ReferralPlan)
class ReferralPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'level_1_rate', 'level_2_rate', 'is_active', 'created_at')

@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ('id', 'referrer', 'referred_user', 'referral_code', 'level', 'status', 'created_at')
    list_filter = ('level', 'status', 'created_at')
    search_fields = ('referrer__username', 'referred_user__username', 'referral_code')

@admin.register(ReferralReward)
class ReferralRewardAdmin(admin.ModelAdmin):
    list_display = ('id', 'beneficiary_user', 'source_user', 'source_position', 'level', 'rate', 'reward_amount', 'created_at')
    list_filter = ('level', 'created_at')
    search_fields = ('beneficiary_user__username', 'source_user__username')
