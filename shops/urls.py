from django.urls import path
from . import views

urlpatterns = [
    path('my/', views.my_shops, name='my_shops'),
    path('create/', views.create_shop, name='create_shop'),
    path('<slug:shop_slug>/dashboard/', views.shop_dashboard, name='shop_dashboard'),
    path('<slug:shop_slug>/manage/', views.shop_manage, name='shop_manage'),
    path('<slug:shop_slug>/add-product/', views.add_product_page, name='shop_add_product'),
    path('<slug:shop_slug>/edit-product/<int:product_id>/', views.edit_product_page, name='shop_edit_product'),
    path('<slug:shop_slug>/download/', views.download_shop_export, name='download_shop_export'),
    
    path('<slug:shop_slug>/delete-product/<int:product_id>/', views.delete_product, name='delete_product'),
    path('<slug:shop_slug>/delete-warehouse/<int:warehouse_id>/', views.delete_warehouse, name='delete_warehouse'),
    path('<slug:shop_slug>/delete-category/<int:category_id>/', views.delete_category, name='delete_category'),
    path('<slug:shop_slug>/delete-brand/<int:brand_id>/', views.delete_brand, name='delete_brand'),
    path('<slug:shop_slug>/delete-news/<int:news_id>/', views.delete_news, name='delete_news'),
    
    path('<slug:shop_slug>/cart/', views.cart_view, name='cart_view'),
    path('<slug:shop_slug>/add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('<slug:shop_slug>/remove-from-cart/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('<slug:shop_slug>/update-cart/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    path('<slug:shop_slug>/checkout/', views.checkout, name='checkout'),
    path('<slug:shop_slug>/order-confirmation/<int:order_id>/', views.order_confirmation, name='order_confirmation'),
    path('<slug:shop_slug>/my-orders/', views.my_orders, name='my_orders'),
    
    path('<slug:shop_slug>/favorites/', views.favorites_list, name='favorites_list'),
    path('<slug:shop_slug>/add-to-favorites/<int:product_id>/', views.add_to_favorites, name='add_to_favorites'),
    path('<slug:shop_slug>/remove-from-favorites/<int:product_id>/', views.remove_from_favorites, name='remove_from_favorites'),
    
    path('<slug:shop_slug>/buyer/login/', views.shop_customer_login, name='shop_customer_login'),
    path('<slug:shop_slug>/buyer/register/', views.shop_customer_register, name='shop_customer_register'),
    path('<slug:shop_slug>/profile/', views.customer_profile, name='customer_profile'),
    path('<slug:shop_slug>/orders/', views.customer_orders, name='customer_orders'),
    path('<slug:shop_slug>/order/<int:order_id>/', views.customer_order_detail, name='customer_order_detail'),
    
    path('<slug:shop_slug>/search/', views.search_products, name='search_products'),
    
    path('<slug:shop_slug>/news/', views.shop_news, name='shop_news'),
    path('<slug:shop_slug>/news/<int:news_id>/', views.news_detail, name='news_detail'),
    path('<slug:shop_slug>/category/<int:category_id>/', views.category_products, name='category_products'),
    path('<slug:shop_slug>/product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('<slug:shop_slug>/', views.shop_front, name='shop_front'),

    path('<slug:shop_slug>/payment/<int:order_id>/', views.payment_page, name='payment_page'),
    path('<slug:shop_slug>/process-payment/<int:order_id>/', views.process_payment, name='process_payment'),
    path('<slug:shop_slug>/payment-success/<int:order_id>/', views.payment_success, name='payment_success'),
    path('<slug:shop_slug>/payment-failed/<int:order_id>/', views.payment_failed, name='payment_failed'),
]
