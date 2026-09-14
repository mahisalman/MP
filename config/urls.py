"""
URL configuration for config project.
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("wallet/", include("wallet.urls")),
    path("rewards/", include("rewards.urls")),
    path("referrals/", include("referrals.urls")),
    path("withdrawals/", include("withdrawals.urls")),
]
