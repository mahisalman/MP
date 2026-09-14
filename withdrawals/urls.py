from django.urls import path
from . import views

app_name = 'withdrawals'

urlpatterns = [
    path('', views.withdrawal_list_view, name='list'),
    path('request/', views.withdrawal_request_view, name='request'),
]
