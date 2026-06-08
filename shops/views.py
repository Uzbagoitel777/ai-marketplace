import time
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.text import slugify
from .models import Shop, Category, Brand, Product, News

# ========== Панель управления (для владельца) ==========

@login_required
def my_shops(request):
    """Список магазинов текущего пользователя"""
    shops = request.user.shops.all()
    return render(request, 'shops/my_shops.html', {'shops': shops})

@login_required
def create_shop(request):
    """Создание нового магазина"""
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        
        if not name:
            messages.error(request, 'Название магазина обязательно')
            return redirect('create_shop')
        
        # Создаем slug из названия
        slug = slugify(name)
        
        # Если slug пустой (например, только спецсимволы)
        if not slug:
            slug = f"shop-{request.user.id}-{int(time.time())}"
        
        # Проверяем уникальность slug
        original_slug = slug
        counter = 1
        while Shop.objects.filter(slug=slug).exists():
            slug = f"{original_slug}-{counter}"
            counter += 1
        
        shop = Shop.objects.create(
            owner=request.user,
            name=name,
            slug=slug,
            description=description
        )
        
        messages.success(request, f'Магазин "{name}" успешно создан!')
        return redirect('my_shops')
    
    return render(request, 'shops/create_shop.html')

@login_required
def shop_dashboard(request, shop_slug):
    """Панель управления магазином (статистика)"""
    shop = get_object_or_404(Shop, slug=shop_slug, owner=request.user)
    
    # Статистика
    products_count = shop.products.count()
    categories_count = shop.categories.count()
    brands_count = shop.brands.count()
    news_count = shop.news.count()
    
    context = {
        'shop': shop,
        'products_count': products_count,
        'categories_count': categories_count,
        'brands_count': brands_count,
        'news_count': news_count,
    }
    return render(request, 'shops/dashboard.html', context)

@login_required
def shop_manage(request, shop_slug):
    """Упрощённая страница управления магазином (товары, категории, новости)"""
    shop = get_object_or_404(Shop, slug=shop_slug, owner=request.user)
    
    # Получаем все данные
    products = shop.products.all()
    categories = shop.categories.all()
    brands = shop.brands.all()
    news_list = shop.news.all()
    
    context = {
        'shop': shop,
        'products': products,
        'categories': categories,
        'brands': brands,
        'news_list': news_list,
    }
    return render(request, 'shops/shop_manage.html', context)

@login_required
def delete_product(request, shop_slug, product_id):
    """Удаление товара"""
    shop = get_object_or_404(Shop, slug=shop_slug, owner=request.user)
    product = get_object_or_404(Product, id=product_id, shop=shop)
    product.delete()
    messages.success(request, f'Товар "{product.name}" удалён')
    return redirect('shop_manage', shop_slug=shop.slug)

@login_required
def delete_category(request, shop_slug, category_id):
    """Удаление категории"""
    shop = get_object_or_404(Shop, slug=shop_slug, owner=request.user)
    category = get_object_or_404(Category, id=category_id, shop=shop)
    category.delete()
    messages.success(request, f'Категория "{category.name}" удалена')
    return redirect('shop_manage', shop_slug=shop.slug)

@login_required
def delete_news(request, shop_slug, news_id):
    """Удаление новости"""
    shop = get_object_or_404(Shop, slug=shop_slug, owner=request.user)
    news = get_object_or_404(News, id=news_id, shop=shop)
    news.delete()
    messages.success(request, f'Новость "{news.title}" удалена')
    return redirect('shop_manage', shop_slug=shop.slug)

# ========== Публичная витрина (для покупателей) ==========

def shop_front(request, shop_slug):
    """Главная страница магазина (витрина)"""
    shop = get_object_or_404(Shop, slug=shop_slug)
    products = shop.products.all()[:12]
    categories = shop.categories.all()
    news_list = shop.news.all()[:3]
    
    context = {
        'shop': shop,
        'products': products,
        'categories': categories,
        'news_list': news_list,
    }
    return render(request, 'shops/front_index.html', context)

def product_detail(request, shop_slug, product_id):
    """Страница отдельного товара"""
    shop = get_object_or_404(Shop, slug=shop_slug)
    product = get_object_or_404(Product, id=product_id, shop=shop)
    
    context = {
        'shop': shop,
        'product': product,
    }
    return render(request, 'shops/product_detail.html', context)

def category_products(request, shop_slug, category_id):
    """Товары по категории"""
    shop = get_object_or_404(Shop, slug=shop_slug)
    category = get_object_or_404(Category, id=category_id, shop=shop)
    products = category.products.all()
    
    context = {
        'shop': shop,
        'category': category,
        'products': products,
    }
    return render(request, 'shops/category_products.html', context)

def shop_news(request, shop_slug):
    """Все новости магазина"""
    shop = get_object_or_404(Shop, slug=shop_slug)
    news_list = shop.news.all()
    
    context = {
        'shop': shop,
        'news_list': news_list,
    }
    return render(request, 'shops/news_list.html', context)

def news_detail(request, shop_slug, news_id):
    """Детальная страница новости"""
    shop = get_object_or_404(Shop, slug=shop_slug)
    news = get_object_or_404(News, id=news_id, shop=shop)
    
    context = {
        'shop': shop,
        'news': news,
    }
    return render(request, 'shops/news_detail.html', context)