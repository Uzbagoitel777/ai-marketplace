import time
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils.text import slugify
from django.db import models as django_models
from django.core.paginator import Paginator
from django.contrib.auth.models import User
from .models import Shop, Category, Brand, Product, News, Cart, CartItem, Order, OrderItem, Favorite, Payment


def home(request):
    """Главная страница - витрина всех магазинов"""
    shops = Shop.objects.all().order_by('-created_at')
    
    # Поиск магазинов
    query = request.GET.get('q', '')
    if query:
        shops = shops.filter(name__icontains=query)
    
    # Пагинация
    paginator = Paginator(shops, 9)
    page_number = request.GET.get('page', 1)
    shops_page = paginator.get_page(page_number)
    
    # Статистика для главной
    total_shops = Shop.objects.count()
    total_products = Product.objects.count()
    total_users = User.objects.count()
    
    context = {
        'shops': shops_page,
        'query': query,
        'total_shops': total_shops,
        'total_products': total_products,
        'total_users': total_users,
    }
    return render(request, 'home.html', context)


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
        
        slug = slugify(name)
        
        if not slug:
            slug = f"shop-{request.user.id}-{int(time.time())}"
        
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
    """Панель управления магазином со статистикой и аналитикой"""
    shop = get_object_or_404(Shop, slug=shop_slug, owner=request.user)
    
    # Статистика товаров
    products_count = shop.products.count()
    categories_count = shop.categories.count()
    brands_count = shop.brands.count()
    news_count = shop.news.count()
    
    # Статистика заказов
    orders = Order.objects.filter(shop=shop)
    orders_count = orders.count()
    total_revenue = orders.aggregate(total=django_models.Sum('total_amount'))['total'] or 0
    completed_orders = orders.filter(status='delivered').count()
    
    # Популярные товары
    popular_products = Product.objects.filter(
        shop=shop,
        orderitem__isnull=False
    ).annotate(
        total_sold=django_models.Sum('orderitem__quantity')
    ).order_by('-total_sold')[:5]
    
    # Заказы по статусам
    orders_by_status = {
        'new': orders.filter(status='new').count(),
        'processing': orders.filter(status='processing').count(),
        'shipped': orders.filter(status='shipped').count(),
        'delivered': orders.filter(status='delivered').count(),
        'cancelled': orders.filter(status='cancelled').count(),
    }
    
    # Заказы по дням (последние 7 дней)
    from datetime import datetime, timedelta
    today = datetime.now().date()
    orders_by_day = []
    for i in range(7):
        day = today - timedelta(days=i)
        day_orders = orders.filter(created_at__date=day).count()
        day_revenue = orders.filter(created_at__date=day).aggregate(total=django_models.Sum('total_amount'))['total'] or 0
        orders_by_day.append({
            'date': day.strftime('%d.%m'),
            'count': day_orders,
            'revenue': float(day_revenue)
        })
    
    context = {
        'shop': shop,
        'products_count': products_count,
        'categories_count': categories_count,
        'brands_count': brands_count,
        'news_count': news_count,
        'orders_count': orders_count,
        'total_revenue': total_revenue,
        'completed_orders': completed_orders,
        'popular_products': popular_products,
        'orders_by_status': orders_by_status,
        'orders_by_day': orders_by_day,
    }
    return render(request, 'shops/dashboard.html', context)

@login_required
def shop_manage(request, shop_slug):
    """Упрощённая страница управления магазином (товары, категории, новости)"""
    shop = get_object_or_404(Shop, slug=shop_slug, owner=request.user)
    
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
    """Главная страница магазина (витрина) с пагинацией"""
    shop = get_object_or_404(Shop, slug=shop_slug)
    categories = shop.categories.all()
    news_list = shop.news.all()[:3]
    
    products_list = shop.products.all()
    paginator = Paginator(products_list, 12)
    page_number = request.GET.get('page', 1)
    products = paginator.get_page(page_number)
    
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

def search_products(request, shop_slug):
    """Поиск товаров в магазине"""
    shop = get_object_or_404(Shop, slug=shop_slug)
    query = request.GET.get('q', '')
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')
    
    products = shop.products.all()
    
    if query:
        products = products.filter(
            django_models.Q(name__icontains=query) |
            django_models.Q(description__icontains=query) |
            django_models.Q(brand__name__icontains=query)
        )
    
    if min_price:
        try:
            products = products.filter(price__gte=float(min_price))
        except ValueError:
            pass
    
    if max_price:
        try:
            products = products.filter(price__lte=float(max_price))
        except ValueError:
            pass
    
    context = {
        'shop': shop,
        'products': products,
        'query': query,
        'min_price': min_price,
        'max_price': max_price,
        'categories': shop.categories.all(),
        'news_list': shop.news.all()[:3],
    }
    return render(request, 'shops/search_results.html', context)

# ========== Корзина и заказы ==========

def get_or_create_cart(request, shop_slug):
    """Получить или создать корзину для текущего пользователя и магазина"""
    if not request.user.is_authenticated:
        return None
    
    shop = get_object_or_404(Shop, slug=shop_slug)
    cart, created = Cart.objects.get_or_create(
        user=request.user,
        shop=shop,
        defaults={'user': request.user, 'shop': shop}
    )
    return cart

@login_required
def cart_view(request, shop_slug):
    """Страница корзины"""
    shop = get_object_or_404(Shop, slug=shop_slug)
    cart = get_or_create_cart(request, shop_slug)
    
    if not cart:
        return redirect('login')
    
    context = {
        'shop': shop,
        'cart': cart,
    }
    return render(request, 'shops/cart.html', context)

@login_required
def add_to_cart(request, shop_slug, product_id):
    """Добавление товара в корзину"""
    if request.method == 'POST':
        shop = get_object_or_404(Shop, slug=shop_slug)
        product = get_object_or_404(Product, id=product_id, shop=shop)
        cart = get_or_create_cart(request, shop_slug)
        
        quantity = int(request.POST.get('quantity', 1))
        
        if quantity > product.stock:
            messages.error(request, f'Товара "{product.name}" в наличии только {product.stock} шт.')
            return redirect('product_detail', shop_slug=shop_slug, product_id=product_id)
        
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )
        
        if not created:
            cart_item.quantity += quantity
            cart_item.save()
        
        messages.success(request, f'Товар "{product.name}" добавлен в корзину')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'cart_total': cart.total_items(),
                'cart_price': str(cart.total_price())
            })
        
        return redirect('cart_view', shop_slug=shop_slug)
    
    return redirect('shop_front', shop_slug=shop_slug)

@login_required
def remove_from_cart(request, shop_slug, item_id):
    """Удаление товара из корзины"""
    cart = get_or_create_cart(request, shop_slug)
    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
    cart_item.delete()
    messages.success(request, 'Товар удалён из корзины')
    return redirect('cart_view', shop_slug=shop_slug)

@login_required
def update_cart_item(request, shop_slug, item_id):
    """Обновление количества товара в корзине"""
    if request.method == 'POST':
        cart = get_or_create_cart(request, shop_slug)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
        
        quantity = int(request.POST.get('quantity', 1))
        
        if quantity <= 0:
            cart_item.delete()
        else:
            if quantity > cart_item.product.stock:
                messages.error(request, f'Товара "{cart_item.product.name}" в наличии только {cart_item.product.stock} шт.')
            else:
                cart_item.quantity = quantity
                cart_item.save()
        
        return redirect('cart_view', shop_slug=shop_slug)
    
    return redirect('cart_view', shop_slug=shop_slug)

@login_required
def checkout(request, shop_slug):
    """Оформление заказа"""
    shop = get_object_or_404(Shop, slug=shop_slug)
    cart = get_or_create_cart(request, shop_slug)
    
    if cart.items.count() == 0:
        messages.error(request, 'Корзина пуста')
        return redirect('cart_view', shop_slug=shop_slug)
    
    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        comment = request.POST.get('comment', '')
        
        if not all([full_name, phone, address]):
            messages.error(request, 'Пожалуйста, заполните все обязательные поля')
            return redirect('checkout', shop_slug=shop_slug)
        
        order = Order.objects.create(
            user=request.user,
            shop=shop,
            full_name=full_name,
            phone=phone,
            address=address,
            comment=comment
        )
        
        for cart_item in cart.items.all():
            if cart_item.quantity <= cart_item.product.stock:
                OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    quantity=cart_item.quantity,
                    price=cart_item.product.price
                )
                cart_item.product.stock -= cart_item.quantity
                cart_item.product.save()
        
        order.update_total()
        cart.items.all().delete()
        
        messages.success(request, f'Заказ #{order.id} успешно оформлен!')
        return redirect('order_confirmation', shop_slug=shop_slug, order_id=order.id)
    
    context = {
        'shop': shop,
        'cart': cart,
    }
    return render(request, 'shops/checkout.html', context)

@login_required
def order_confirmation(request, shop_slug, order_id):
    """Страница подтверждения заказа"""
    shop = get_object_or_404(Shop, slug=shop_slug)
    order = get_object_or_404(Order, id=order_id, user=request.user, shop=shop)
    
    context = {
        'shop': shop,
        'order': order,
    }
    return render(request, 'shops/order_confirmation.html', context)

@login_required
def my_orders(request, shop_slug):
    """Список заказов пользователя в магазине"""
    shop = get_object_or_404(Shop, slug=shop_slug)
    orders = Order.objects.filter(user=request.user, shop=shop).order_by('-created_at')
    
    context = {
        'shop': shop,
        'orders': orders,
    }
    return render(request, 'shops/my_orders.html', context)

# ========== Избранное (лайки) ==========

@login_required
def add_to_favorites(request, shop_slug, product_id):
    """Добавить товар в избранное"""
    shop = get_object_or_404(Shop, slug=shop_slug)
    product = get_object_or_404(Product, id=product_id, shop=shop)
    
    favorite, created = Favorite.objects.get_or_create(
        user=request.user,
        product=product
    )
    
    if created:
        messages.success(request, f'Товар "{product.name}" добавлен в избранное')
    else:
        messages.info(request, f'Товар "{product.name}" уже в избранном')
    
    return redirect('product_detail', shop_slug=shop_slug, product_id=product_id)

@login_required
def remove_from_favorites(request, shop_slug, product_id):
    """Удалить товар из избранного"""
    shop = get_object_or_404(Shop, slug=shop_slug)
    product = get_object_or_404(Product, id=product_id, shop=shop)
    
    Favorite.objects.filter(user=request.user, product=product).delete()
    messages.success(request, f'Товар "{product.name}" удалён из избранного')
    
    return redirect('product_detail', shop_slug=shop_slug, product_id=product_id)

@login_required
def favorites_list(request, shop_slug):
    """Страница избранных товаров"""
    shop = get_object_or_404(Shop, slug=shop_slug)
    favorites = Favorite.objects.filter(user=request.user, product__shop=shop)
    
    context = {
        'shop': shop,
        'favorites': favorites,
    }
    return render(request, 'shops/favorites.html', context)

# ========== Личный кабинет покупателя ==========

from accounts.models import CustomerProfile

@login_required
def customer_profile(request, shop_slug):
    """Личный кабинет покупателя"""
    shop = get_object_or_404(Shop, slug=shop_slug)
    profile, created = CustomerProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        
        profile.phone = phone
        profile.address = address
        profile.save()
        
        messages.success(request, 'Профиль успешно обновлён')
        return redirect('customer_profile', shop_slug=shop_slug)
    
    # Заказы пользователя
    orders = Order.objects.filter(user=request.user, shop=shop).order_by('-created_at')
    
    # Избранные товары
    favorites = Favorite.objects.filter(user=request.user, product__shop=shop)
    
    context = {
        'shop': shop,
        'profile': profile,
        'orders': orders,
        'favorites': favorites,
    }
    return render(request, 'shops/customer_profile.html', context)

@login_required
def customer_orders(request, shop_slug):
    """Страница заказов покупателя"""
    shop = get_object_or_404(Shop, slug=shop_slug)
    orders = Order.objects.filter(user=request.user, shop=shop).order_by('-created_at')
    
    context = {
        'shop': shop,
        'orders': orders,
    }
    return render(request, 'shops/customer_orders.html', context)

@login_required
def customer_order_detail(request, shop_slug, order_id):
    """Детальная страница заказа"""
    shop = get_object_or_404(Shop, slug=shop_slug)
    order = get_object_or_404(Order, id=order_id, user=request.user, shop=shop)
    
    context = {
        'shop': shop,
        'order': order,
    }
    return render(request, 'shops/customer_order_detail.html', context)

# ========== Тестовая оплата ==========

@login_required
def payment_page(request, shop_slug, order_id):
    """Страница оплаты заказа"""
    shop = get_object_or_404(Shop, slug=shop_slug)
    order = get_object_or_404(Order, id=order_id, user=request.user, shop=shop)
    
    # Создаем или получаем платеж
    payment, created = Payment.objects.get_or_create(
        order=order,
        defaults={
            'amount': order.total_amount,
            'status': 'pending'
        }
    )
    
    context = {
        'shop': shop,
        'order': order,
        'payment': payment,
    }
    return render(request, 'shops/payment.html', context)

@login_required
def process_payment(request, shop_slug, order_id):
    """Обработка тестового платежа"""
    if request.method == 'POST':
        shop = get_object_or_404(Shop, slug=shop_slug)
        order = get_object_or_404(Order, id=order_id, user=request.user, shop=shop)
        payment = Payment.objects.get(order=order)
        
        # Получаем способ оплаты из формы
        payment_method = request.POST.get('payment_method', 'test')
        
        # Симуляция успешного платежа
        import uuid
        transaction_id = str(uuid.uuid4())[:8]
        
        # Обновляем статус платежа
        payment.status = 'paid'
        payment.payment_method = payment_method
        payment.transaction_id = transaction_id
        payment.save()
        
        # Обновляем статус заказа
        order.status = 'processing'
        order.save()
        
        messages.success(request, f'Оплата прошла успешно! Номер транзакции: {transaction_id}')
        return redirect('payment_success', shop_slug=shop_slug, order_id=order.id)
    
    return redirect('payment_page', shop_slug=shop_slug, order_id=order_id)

@login_required
def payment_success(request, shop_slug, order_id):
    """Страница успешной оплаты"""
    shop = get_object_or_404(Shop, slug=shop_slug)
    order = get_object_or_404(Order, id=order_id, user=request.user, shop=shop)
    payment = Payment.objects.get(order=order)
    
    context = {
        'shop': shop,
        'order': order,
        'payment': payment,
    }
    return render(request, 'shops/payment_success.html', context)

@login_required
def payment_failed(request, shop_slug, order_id):
    """Страница неудачной оплаты (для демонстрации)"""
    shop = get_object_or_404(Shop, slug=shop_slug)
    order = get_object_or_404(Order, id=order_id, user=request.user, shop=shop)
    
    context = {
        'shop': shop,
        'order': order,
    }
    return render(request, 'shops/payment_failed.html', context)