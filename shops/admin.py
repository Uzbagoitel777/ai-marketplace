from django.contrib import admin
from django.urls import path, reverse
from django.shortcuts import redirect
from django.core.management import call_command
from django.utils.html import format_html
from .models import Shop, Category, Brand, Product, News

@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'view_shop_link', 'generate_demo_button', 'created_at']
    list_filter = ['owner']
    search_fields = ['name', 'owner__username']
    prepopulated_fields = {'slug': ('name',)}
    
    def view_shop_link(self, obj):
        if obj.slug:
            url = reverse('shop_front', args=[obj.slug])
            return format_html('<a href="{}" target="_blank">🔗 Смотреть магазин</a>', url)
        return "—"
    view_shop_link.short_description = 'Витрина'
    
    def generate_demo_button(self, obj):
        url = reverse('admin:generate_demo', args=[obj.pk])
        return format_html('<a class="button" href="{}" style="background: #4CAF50; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px;">📦 Создать 20 тестовых товаров</a>', url)
    generate_demo_button.short_description = 'Демо-товары'
    generate_demo_button.allow_tags = True
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<path:object_id>/generate_demo/', self.admin_site.admin_view(self.generate_demo), name='generate_demo'),
        ]
        return custom_urls + urls
    
    def generate_demo(self, request, object_id):
        from shops.models import Shop
        try:
            shop = Shop.objects.get(id=object_id)
            
            # Проверяем наличие категорий
            if not shop.categories.exists():
                self.message_user(request, f'Ошибка: В магазине "{shop.name}" нет категорий. Сначала создайте хотя бы одну категорию.', level='ERROR')
                return redirect('admin:shops_shop_changelist')
            
            # Запускаем генерацию товаров
            call_command('generate_demo_products', shop.slug, count=20)
            self.message_user(request, f'Успешно создано 20 тестовых товаров для магазина "{shop.name}"')
        except Shop.DoesNotExist:
            self.message_user(request, 'Магазин не найден', level='ERROR')
        except Exception as e:
            self.message_user(request, f'Ошибка при генерации: {str(e)}', level='ERROR')
        
        return redirect('admin:shops_shop_changelist')

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'shop', 'order']
    list_filter = ['shop']
    search_fields = ['name']
    list_editable = ['order']

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
    list_editable = ['price', 'stock']

@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ['title', 'shop', 'created_at']
    list_filter = ['shop']
    search_fields = ['title']