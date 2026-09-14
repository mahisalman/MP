from django.urls import path
from . import views

app_name = 'rewards'

urlpatterns = [
    path('', views.positions_list_view, name='positions'),
    path('allocate/', views.allocate_position_view, name='allocate'),
    path('<int:position_id>/', views.position_detail_view, name='detail'),
]
