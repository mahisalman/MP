from django.contrib import admin
from .models import Wallet, WalletTransaction

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'available_balance', 'locked_balance', 'lifetime_credited', 'lifetime_debited', 'updated_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('available_balance', 'locked_balance', 'lifetime_credited', 'lifetime_debited', 'created_at', 'updated_at')

@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'wallet', 'transaction_type', 'direction', 'amount', 'balance_after', 'created_at')
    list_filter = ('transaction_type', 'direction', 'created_at')
    search_fields = ('wallet__user__username', 'description', 'idempotency_key')
    readonly_fields = ('wallet', 'transaction_type', 'direction', 'amount', 'balance_before', 'balance_after', 'description', 'idempotency_key', 'created_at')
