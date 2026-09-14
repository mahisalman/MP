from django.urls import path
from . import views

app_name = 'wallet'

urlpatterns = [
    path('', views.wallet_detail_view, name='detail'),
    path('deposit/', views.demo_deposit_view, name='deposit'),
]
