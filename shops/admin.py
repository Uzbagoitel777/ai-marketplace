from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import Shop, Category, Brand, Product, News

@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'view_shop_link', 'created_at']
    list_filter = ['owner']
    search_fields = ['name', 'owner__username']
    prepopulated_fields = {'slug': ('name',)}
    
    def view_shop_link(self, obj):
        if obj.slug:
            url = reverse('shop_front', args=[obj.slug])
            return format_html('<a href="{}" target="_blank">🔗 Смотреть магазин</a>', url)
        return "—"
    view_shop_link.short_description = 'Витрина'

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'shop', 'order']
    list_filter = ['shop']
    search_fields = ['name']

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name', 'shop']
    list_filter = ['shop']
    search_fields = ['name']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'shop', 'category', 'brand', 'price', 'stock']
    list_filter = ['shop', 'category', 'brand']
    search_fields = ['name', 'description']

@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ['title', 'shop', 'created_at']
    list_filter = ['shop']
    search_fields = ['title']