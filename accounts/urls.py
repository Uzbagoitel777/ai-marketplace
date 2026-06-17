from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', views.register_customer, name='register_customer'),
    path('register-seller/', views.register_seller, name='register_seller'),
    path('pricing/', views.pricing, name='pricing'),
    path('pricing/<str:plan_code>/', views.choose_plan, name='choose_plan'),
    path('reviews/', views.platform_reviews, name='platform_reviews'),
]
