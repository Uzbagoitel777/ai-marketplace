from django.urls import path
from . import views

urlpatterns = [
    # Панель управления (для владельца)
    path('my/', views.my_shops, name='my_shops'),
    path('create/', views.create_shop, name='create_shop'),
    path('<slug:shop_slug>/dashboard/', views.shop_dashboard, name='shop_dashboard'),
    path('<slug:shop_slug>/manage/', views.shop_manage, name='shop_manage'),
    
    # Удаление
    path('<slug:shop_slug>/delete-product/<int:product_id>/', views.delete_product, name='delete_product'),
    path('<slug:shop_slug>/delete-category/<int:category_id>/', views.delete_category, name='delete_category'),
    path('<slug:shop_slug>/delete-news/<int:news_id>/', views.delete_news, name='delete_news'),
    
    # Публичная витрина (для покупателей)
    path('<slug:shop_slug>/news/', views.shop_news, name='shop_news'),
    path('<slug:shop_slug>/news/<int:news_id>/', views.news_detail, name='news_detail'),
    path('<slug:shop_slug>/category/<int:category_id>/', views.category_products, name='category_products'),
    path('<slug:shop_slug>/product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('<slug:shop_slug>/', views.shop_front, name='shop_front'),
]