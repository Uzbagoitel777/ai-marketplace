from django.urls import path
from . import views

urlpatterns = [
    path('', views.admin_dashboard, name='admin_dashboard'),
    path('users/', views.admin_users, name='admin_users'),
    path('users/<int:user_id>/', views.admin_user_detail, name='admin_user_detail'),
    path('shops/', views.admin_shops, name='admin_shops'),
    path('orders/', views.admin_orders, name='admin_orders'),
    path('orders/<int:order_id>/update-status/', views.admin_update_order_status, name='admin_update_order_status'),
]