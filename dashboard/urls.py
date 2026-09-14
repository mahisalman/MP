from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_view, name='home'),
    path('admin-control/', views.admin_simulation_control_view, name='admin_sim_control'),
]
