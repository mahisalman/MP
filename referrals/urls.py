from django.urls import path
from . import views

app_name = 'referrals'

urlpatterns = [
    path('', views.referrals_view, name='network'),
]
