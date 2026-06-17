from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.ai_create_shop, name='ai_create_shop'),
    path('confirm/', views.confirm_create_shop, name='confirm_create_shop'),
    path('generate-description/', views.generate_product_description_ajax, name='generate_description'),
    path('chat/<slug:shop_slug>/', views.ai_chat, name='ai_chat'),
]
