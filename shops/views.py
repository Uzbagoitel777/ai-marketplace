import io
import json
import time
import zipfile
import re
from decimal import Decimal, InvalidOperation
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.utils.text import slugify
from django.urls import reverse
from django.utils import timezone
from django.db import models as django_models
from django.core.paginator import Paginator
from django.contrib.auth.models import User
from .models import Shop, Category, Brand, Product, News, Warehouse, PaymentAccount, Cart, CartItem, Order, OrderItem, Favorite, Payment
from accounts.models import CustomerProfile, SellerProfile


DELIVERY_SERVICES = {
    'pickup': 'Самовывоз',
    'courier': 'Курьер по городу',
    'cdek': 'СДЭК / транспортная компания',
    'post': 'Почта России',
}


def extract_city(value):
    value = (value or '').strip()
    if not value:
        return ''
    return value.split(',')[0].strip().title()


def calculate_delivery_price(shop, customer_city, service):
    service = service if service in DELIVERY_SERVICES else 'courier'
    shop_city = (shop.city or 'Екатеринбург').strip().lower()
    client_city = (customer_city or '').strip().lower()
    same_city = bool(client_city) and client_city == shop_city
    if service == 'pickup':
        return Decimal('0')
    if service == 'courier':
        return Decimal('250') if same_city else Decimal('550')
    if service == 'cdek':
        return Decimal('390') if same_city else Decimal('690')
    return Decimal('350') if same_city else Decimal('620')


def delivery_options_for(shop, customer_city=''):
    return [
        {'code': code, 'name': name, 'price': calculate_delivery_price(shop, customer_city, code)}
        for code, name in DELIVERY_SERVICES.items()
    ]




def seller_shops_for(user):
    if not user.is_authenticated:
        return Shop.objects.none()
    return user.shops.all().order_by('-created_at')


def cart_summary_for(request, shop):
    if not request.user.is_authenticated or request.user == shop.owner:
        return {'cart_count': 0, 'cart_sum': Decimal('0')}
    cart = Cart.objects.filter(user=request.user, shop=shop).first()
    if not cart:
        return {'cart_count': 0, 'cart_sum': Decimal('0')}
    return {'cart_count': cart.total_items(), 'cart_sum': cart.total_price()}


def dashboard_chart_data(shop, period):
    period_days = {'1d': 1, '7d': 7, '30d': 30, '90d': 90}.get(period, 1)
    now = timezone.now()
    orders = Order.objects.filter(shop=shop, created_at__gte=now - timezone.timedelta(days=period_days))
    points = []
    if period_days == 1:
        for hour in range(24):
            start = now.replace(hour=hour, minute=0, second=0, microsecond=0)
            end = start + timezone.timedelta(hours=1)
            value = orders.filter(created_at__gte=start, created_at__lt=end).aggregate(total=django_models.Sum('total_amount'))['total'] or 0
            points.append({'label': f'{hour:02d}:00', 'value': float(value)})
    else:
        start_day = now.date() - timezone.timedelta(days=period_days - 1)
        for i in range(period_days):
            day = start_day + timezone.timedelta(days=i)
            value = orders.filter(created_at__date=day).aggregate(total=django_models.Sum('total_amount'))['total'] or 0
            points.append({'label': day.strftime('%d.%m'), 'value': float(value)})
    max_value = max([p['value'] for p in points] or [0]) or 1
    svg_points = []
    width, height, pad = 760, 260, 28
    count = max(1, len(points) - 1)
    for idx, point in enumerate(points):
        x = pad + (width - pad * 2) * idx / count
        y = height - pad - ((height - pad * 2) * point['value'] / max_value)
        svg_points.append(f'{x:.1f},{y:.1f}')
    return points, ' '.join(svg_points), max_value


def home(request):
    if request.user.is_authenticated and not request.user.is_superuser:
        try:
            SellerProfile.objects.get_or_create(user=request.user)
            return redirect('my_shops')
        except Exception:
            pass
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_dashboard')
    total_shops = Shop.objects.count()
    total_products = Product.objects.count()
    total_users = User.objects.count()
    total_orders = Order.objects.count()
    total_gmv = Order.objects.aggregate(total=django_models.Sum('total_amount'))['total'] or 0
    sellers_count = SellerProfile.objects.count()
    paid_sellers_count = SellerProfile.objects.exclude(plan=SellerProfile.PLAN_FREE).count()
    estimated_mrr = sum(profile.monthly_fee for profile in SellerProfile.objects.all())
    estimated_commission = float(total_gmv) * 0.03

    return render(request, 'home.html', {
        'total_shops': total_shops,
        'total_products': total_products,
        'total_users': total_users,
        'total_orders': total_orders,
        'total_gmv': total_gmv,
        'sellers_count': sellers_count,
        'paid_sellers_count': paid_sellers_count,
        'estimated_mrr': estimated_mrr,
        'estimated_commission': round(estimated_commission, 2),
    })

@login_required
def my_shops(request):
    profile, _ = SellerProfile.objects.get_or_create(user=request.user)
    shops = request.user.shops.all().order_by('-created_at')
    orders = Order.objects.filter(shop__owner=request.user)
    total_revenue = orders.aggregate(total=django_models.Sum('total_amount'))['total'] or 0
    orders_count = orders.count()
    products_count = Product.objects.filter(shop__owner=request.user).count()

    active_shop = shops.first()
    context = {
        'shops': shops,
        'active_shop': active_shop,
        'seller_profile': profile,
        'orders_count': orders_count,
        'total_revenue': total_revenue,
        'products_count': products_count,
        'can_create_shop': profile.can_create_shop,
        'seller_shops': shops,
        'seller_section': 'summary',
    }
    return render(request, 'shops/my_shops.html', context)

@login_required
def create_shop(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        template_key = request.POST.get('template_key', 'modern')
        city = request.POST.get('city', '').strip()
        address = request.POST.get('address', '').strip()
        
        if not name:
            messages.error(request, 'Название магазина обязательно')
            return redirect('create_shop')
        if not city or not address:
            messages.error(request, 'Укажите город и адрес нахождения магазина')
            return redirect('create_shop')
        
        profile, _ = SellerProfile.objects.get_or_create(user=request.user)
        if not profile.can_create_shop:
            messages.error(request, f'На тарифе {profile.plan_config["name"]} можно создать максимум {profile.shop_limit} магазин(ов). Перейдите на другой тариф.')
            return redirect('pricing')

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
            description=description,
            template_key=template_key,
            city=city,
            address=address,
            assistant_level=profile.plan_config.get('assistant', 'basic'),
            is_demo=profile.plan == SellerProfile.PLAN_FREE,
            hosting_enabled=profile.plan == SellerProfile.PLAN_BUSINESS,
        )
        Warehouse.objects.create(shop=shop, name='Главный магазин', city=city, address=address, delivery_services='Самовывоз, Курьер, СДЭК', is_pickup_point=True)
        PaymentAccount.objects.get_or_create(shop=shop)
        
        messages.success(request, f'Магазин "{name}" успешно создан!')
        return redirect('my_shops')
    
    return render(request, 'shops/create_shop.html')

@login_required
def shop_dashboard(request, shop_slug):
    shop = get_object_or_404(Shop, slug=shop_slug, owner=request.user)
    
    products_count = shop.products.count()
    categories_count = shop.categories.count()
    brands_count = shop.brands.count()
    news_count = shop.news.count()
    
    orders = Order.objects.filter(shop=shop)
    orders_count = orders.count()
    total_revenue = orders.aggregate(total=django_models.Sum('total_amount'))['total'] or 0
    completed_orders = orders.filter(status='delivered').count()
    cancelled_orders = orders.filter(status='cancelled').count()
    conversion = 13 if products_count else 0
    avg_order = round(float(total_revenue) / orders_count, 2) if orders_count else 0
    recent_orders = orders.select_related('user').prefetch_related('items__product')[:12]
    section = request.GET.get('section', 'summary')
    period = request.GET.get('period', '1d')
    chart_points, chart_svg_points, chart_max_value = dashboard_chart_data(shop, period)
    
    popular_products = Product.objects.filter(
        shop=shop,
        orderitem__isnull=False
    ).annotate(
        total_sold=django_models.Sum('orderitem__quantity')
    ).order_by('-total_sold')[:5]
    
    orders_by_status = {
        'new': orders.filter(status='new').count(),
        'processing': orders.filter(status='processing').count(),
        'shipped': orders.filter(status='shipped').count(),
        'delivered': orders.filter(status='delivered').count(),
        'cancelled': orders.filter(status='cancelled').count(),
    }
    
    
    context = {
        'shop': shop,
        'products_count': products_count,
        'categories_count': categories_count,
        'brands_count': brands_count,
        'news_count': news_count,
        'orders_count': orders_count,
        'total_revenue': total_revenue,
        'completed_orders': completed_orders,
        'cancelled_orders': cancelled_orders,
        'conversion': conversion,
        'avg_order': avg_order,
        'recent_orders': recent_orders,
        'section': section,
        'products': shop.products.select_related('category', 'brand')[:30],
        'popular_products': popular_products,
        'orders_by_status': orders_by_status,
        'period': period,
        'chart_points': chart_points,
        'chart_svg_points': chart_svg_points,
        'chart_max_value': chart_max_value,
        'seller_shops': seller_shops_for(request.user),
        'seller_section': 'orders' if section == 'orders' else 'prices' if section == 'prices' else 'analytics' if section == 'analytics' else 'summary',
    }
    return render(request, 'shops/dashboard.html', context)

@login_required
def shop_manage(request, shop_slug):
    shop = get_object_or_404(Shop, slug=shop_slug, owner=request.user)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create_category':
            name = request.POST.get('name', '').strip()
            if name:
                Category.objects.get_or_create(shop=shop, name=name, defaults={'order': shop.categories.count() + 1})
                messages.success(request, f'Категория «{name}» добавлена')
            else:
                messages.error(request, 'Название категории обязательно')
            return redirect('shop_manage', shop_slug=shop.slug)

        if action == 'create_brand':
            name = request.POST.get('name', '').strip()
            description = request.POST.get('description', '').strip()
            if name:
                Brand.objects.get_or_create(shop=shop, name=name, defaults={'description': description})
                messages.success(request, f'Бренд «{name}» добавлен')
            else:
                messages.error(request, 'Название бренда обязательно')
            return redirect('shop_manage', shop_slug=shop.slug)

        if action == 'create_news':
            title = request.POST.get('title', '').strip()
            content = request.POST.get('content', '').strip()
            if title and content:
                News.objects.create(shop=shop, title=title, content=content)
                messages.success(request, f'Новость «{title}» опубликована')
            else:
                messages.error(request, 'Для новости нужны заголовок и текст')
            return redirect('shop_manage', shop_slug=shop.slug)

        if action == 'create_product':
            name = request.POST.get('name', '').strip()
            description = request.POST.get('description', '').strip()
            category_id = request.POST.get('category') or None
            brand_id = request.POST.get('brand') or None
            image = request.FILES.get('image')
            image_url = request.POST.get('image_url', '').strip()
            try:
                price = Decimal(request.POST.get('price', '0').replace(',', '.'))
                stock = int(request.POST.get('stock', '0'))
            except (InvalidOperation, ValueError):
                messages.error(request, 'Цена и остаток должны быть числами')
                return redirect('shop_manage', shop_slug=shop.slug)

            if not name or not description or price < 0 or stock < 0:
                messages.error(request, 'Заполните название, описание, корректную цену и остаток')
                return redirect('shop_manage', shop_slug=shop.slug)

            category = Category.objects.filter(id=category_id, shop=shop).first() if category_id else None
            brand = Brand.objects.filter(id=brand_id, shop=shop).first() if brand_id else None
            Product.objects.create(
                shop=shop,
                category=category,
                brand=brand,
                name=name,
                description=description,
                price=price,
                stock=stock,
                image=image,
                image_url=image_url,
            )
            messages.success(request, f'Товар «{name}» добавлен')
            return redirect('shop_manage', shop_slug=shop.slug)

        if action == 'update_product':
            product_id = request.POST.get('product_id')
            product = get_object_or_404(Product, id=product_id, shop=shop)
            name = request.POST.get('name', '').strip()
            description = request.POST.get('description', '').strip()
            category_id = request.POST.get('category') or None
            brand_id = request.POST.get('brand') or None
            image = request.FILES.get('image')
            image_url = request.POST.get('image_url', '').strip()
            try:
                price = Decimal(request.POST.get('price', '0').replace(',', '.'))
                stock = int(request.POST.get('stock', '0'))
            except (InvalidOperation, ValueError):
                messages.error(request, 'Цена и остаток должны быть числами')
                return redirect('shop_manage', shop_slug=shop.slug)

            if not name or not description or price < 0 or stock < 0:
                messages.error(request, 'Заполните название, описание, корректную цену и остаток')
                return redirect('shop_manage', shop_slug=shop.slug)

            product.name = name
            product.description = description
            product.category = Category.objects.filter(id=category_id, shop=shop).first() if category_id else None
            product.brand = Brand.objects.filter(id=brand_id, shop=shop).first() if brand_id else None
            product.price = price
            product.stock = stock
            if image:
                product.image = image
            product.image_url = image_url
            product.save()
            messages.success(request, f'Товар «{product.name}» обновлен')
            return redirect('shop_manage', shop_slug=shop.slug)

        if action == 'update_integrations':
            shop.delivery_enabled = bool(request.POST.get('delivery_enabled'))
            city = request.POST.get('city', '').strip()
            address = request.POST.get('address', '').strip()
            if not city or not address:
                messages.error(request, 'Город и адрес магазина обязательны')
                return redirect('shop_manage', shop_slug=shop.slug)
            shop.city = city
            shop.address = address
            shop.payment_enabled = bool(request.POST.get('payment_enabled'))
            shop.delivery_description = request.POST.get('delivery_description', '').strip()
            shop.payment_methods = request.POST.get('payment_methods', '').strip()
            try:
                shop.delivery_price = Decimal(request.POST.get('delivery_price', '0').replace(',', '.'))
            except InvalidOperation:
                shop.delivery_price = Decimal('0')
            shop.save(update_fields=['delivery_enabled', 'city', 'address', 'payment_enabled', 'delivery_description', 'payment_methods', 'delivery_price'])
            messages.success(request, 'Настройки доставки и оплаты обновлены')
            return redirect(f'{reverse("shop_manage", kwargs={"shop_slug": shop.slug})}#integrations')

        if action == 'create_warehouse':
            name = request.POST.get('warehouse_name', '').strip()
            city = request.POST.get('warehouse_city', '').strip()
            address = request.POST.get('warehouse_address', '').strip()
            services = request.POST.get('warehouse_services', '').strip() or 'Самовывоз, Курьер, СДЭК'
            if not name or not city or not address:
                messages.error(request, 'Для склада/магазина нужны название, город и адрес')
                return redirect(f'{reverse("shop_manage", kwargs={"shop_slug": shop.slug})}#integrations')
            Warehouse.objects.create(shop=shop, name=name, city=city, address=address, delivery_services=services, is_pickup_point=bool(request.POST.get('warehouse_pickup')))
            messages.success(request, f'Склад/магазин «{name}» добавлен')
            return redirect(f'{reverse("shop_manage", kwargs={"shop_slug": shop.slug})}#integrations')

        if action == 'update_warehouse':
            warehouse = get_object_or_404(Warehouse, id=request.POST.get('warehouse_id'), shop=shop)
            warehouse.name = request.POST.get('warehouse_name', '').strip() or warehouse.name
            warehouse.city = request.POST.get('warehouse_city', '').strip() or warehouse.city
            warehouse.address = request.POST.get('warehouse_address', '').strip() or warehouse.address
            warehouse.delivery_services = request.POST.get('warehouse_services', '').strip() or warehouse.delivery_services
            warehouse.is_pickup_point = bool(request.POST.get('warehouse_pickup'))
            warehouse.save()
            messages.success(request, f'Склад/магазин «{warehouse.name}» обновлен')
            return redirect(f'{reverse("shop_manage", kwargs={"shop_slug": shop.slug})}#integrations')

        if action == 'update_payment_account':
            account, _ = PaymentAccount.objects.get_or_create(shop=shop)
            account.recipient_name = request.POST.get('recipient_name', '').strip()
            account.bank_name = request.POST.get('bank_name', '').strip()
            account.account_number = request.POST.get('account_number', '').strip()
            account.bik = request.POST.get('bik', '').strip()
            account.inn = request.POST.get('payment_inn', '').strip()
            account.payment_comment = request.POST.get('payment_comment', '').strip()
            account.save()
            messages.success(request, 'Счет для получения оплаты сохранен')
            return redirect(f'{reverse("shop_manage", kwargs={"shop_slug": shop.slug})}#integrations')

        if action == 'update_design':
            theme_color = request.POST.get('theme_color', '#4361ee').strip()
            if not re.match(r'^#[0-9a-fA-F]{6}$', theme_color):
                theme_color = '#4361ee'
            shop.theme_color = theme_color
            shop.custom_css = request.POST.get('custom_css', '').strip()
            shop.save(update_fields=['theme_color', 'custom_css'])
            messages.success(request, 'Дизайн витрины обновлен')
            return redirect('shop_manage', shop_slug=shop.slug)

    products = shop.products.select_related('category', 'brand').all()
    categories = shop.categories.all()
    brands = shop.brands.all()
    news_list = shop.news.all()

    profile, _ = SellerProfile.objects.get_or_create(user=request.user)

    context = {
        'shop': shop,
        'seller_profile': profile,
        'products': products,
        'categories': categories,
        'brands': brands,
        'news_list': news_list,
        'warehouses': shop.warehouses.all().order_by('-created_at'),
        'payment_account': PaymentAccount.objects.filter(shop=shop).first(),
        'seller_shops': seller_shops_for(request.user),
        'seller_section': 'products',
    }
    return render(request, 'shops/shop_manage.html', context)


@login_required
def add_product_page(request, shop_slug):
    shop = get_object_or_404(Shop, slug=shop_slug, owner=request.user)
    categories = shop.categories.all()
    brands = shop.brands.all()

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        category_id = request.POST.get('category') or None
        brand_id = request.POST.get('brand') or None
        image = request.FILES.get('image')
        image_url = request.POST.get('image_url', '').strip()
        try:
            price = Decimal(request.POST.get('price', '0').replace(',', '.'))
            stock = int(request.POST.get('stock', '0'))
        except (InvalidOperation, ValueError):
            messages.error(request, 'Цена и остаток должны быть числами')
            return redirect('shop_add_product', shop_slug=shop.slug)

        if not name or not description or price < 0 or stock < 0:
            messages.error(request, 'Заполните название, описание, корректную цену и остаток')
            return redirect('shop_add_product', shop_slug=shop.slug)

        category = Category.objects.filter(id=category_id, shop=shop).first() if category_id else None
        brand = Brand.objects.filter(id=brand_id, shop=shop).first() if brand_id else None
        product = Product.objects.create(
            shop=shop,
            category=category,
            brand=brand,
            name=name,
            description=description,
            price=price,
            stock=stock,
            image=image,
            image_url=image_url,
        )
        messages.success(request, f'Товар «{product.name}» добавлен')
        return redirect('shop_manage', shop_slug=shop.slug)

    return render(request, 'shops/shop_add_product.html', {
        'shop': shop,
        'categories': categories,
        'brands': brands,
        'seller_shops': seller_shops_for(request.user),
        'seller_section': 'products',
    })

@login_required
def edit_product_page(request, shop_slug, product_id):
    shop = get_object_or_404(Shop, slug=shop_slug, owner=request.user)
    product = get_object_or_404(Product, id=product_id, shop=shop)
    categories = shop.categories.all()
    brands = shop.brands.all()

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        category_id = request.POST.get('category') or None
        brand_id = request.POST.get('brand') or None
        image = request.FILES.get('image')
        image_url = request.POST.get('image_url', '').strip()
        try:
            price = Decimal(request.POST.get('price', '0').replace(',', '.'))
            stock = int(request.POST.get('stock', '0'))
        except (InvalidOperation, ValueError):
            messages.error(request, 'Цена и остаток должны быть числами')
            return redirect('shop_edit_product', shop_slug=shop.slug, product_id=product.id)

        if not name or not description or price < 0 or stock < 0:
            messages.error(request, 'Заполните название, описание, корректную цену и остаток')
            return redirect('shop_edit_product', shop_slug=shop.slug, product_id=product.id)

        product.name = name
        product.description = description
        product.category = Category.objects.filter(id=category_id, shop=shop).first() if category_id else None
        product.brand = Brand.objects.filter(id=brand_id, shop=shop).first() if brand_id else None
        product.price = price
        product.stock = stock
        if image:
            product.image = image
        product.image_url = image_url
        product.save()
        messages.success(request, f'Товар «{product.name}» обновлен')
        return redirect('shop_manage', shop_slug=shop.slug)

    return render(request, 'shops/shop_edit_product.html', {
        'shop': shop,
        'product': product,
        'categories': categories,
        'brands': brands,
        'seller_shops': seller_shops_for(request.user),
        'seller_section': 'products',
    })


@login_required
def delete_warehouse(request, shop_slug, warehouse_id):
    shop = get_object_or_404(Shop, slug=shop_slug, owner=request.user)
    warehouse = get_object_or_404(Warehouse, id=warehouse_id, shop=shop)
    name = warehouse.name
    warehouse.delete()
    messages.success(request, f'Склад/магазин «{name}» удален')
    return redirect(f'{reverse("shop_manage", kwargs={"shop_slug": shop.slug})}#integrations')


@login_required
def delete_product(request, shop_slug, product_id):
    shop = get_object_or_404(Shop, slug=shop_slug, owner=request.user)
    product = get_object_or_404(Product, id=product_id, shop=shop)
    product.delete()
    messages.success(request, f'Товар "{product.name}" удалён')
    return redirect('shop_manage', shop_slug=shop.slug)

@login_required
def delete_category(request, shop_slug, category_id):
    shop = get_object_or_404(Shop, slug=shop_slug, owner=request.user)
    category = get_object_or_404(Category, id=category_id, shop=shop)
    category.delete()
    messages.success(request, f'Категория "{category.name}" удалена')
    return redirect('shop_manage', shop_slug=shop.slug)

@login_required
def delete_brand(request, shop_slug, brand_id):
    shop = get_object_or_404(Shop, slug=shop_slug, owner=request.user)
    brand = get_object_or_404(Brand, id=brand_id, shop=shop)
    brand_name = brand.name
    brand.delete()
    messages.success(request, f'Бренд «{brand_name}» удалён')
    return redirect('shop_manage', shop_slug=shop.slug)


@login_required
def delete_news(request, shop_slug, news_id):
    shop = get_object_or_404(Shop, slug=shop_slug, owner=request.user)
    news = get_object_or_404(News, id=news_id, shop=shop)
    news_title = news.title
    news.delete()
    messages.success(request, f'Новость «{news_title}» удалена')
    return redirect('shop_manage', shop_slug=shop.slug)


def shop_front(request, shop_slug):
    shop = get_object_or_404(Shop, slug=shop_slug)
    if request.user.is_authenticated and request.user == shop.owner and request.GET.get('preview') != '1':
        return redirect('shop_dashboard', shop_slug=shop.slug)
    categories = shop.categories.all()
    news_list = shop.news.all()[:3]
    
    products_list = shop.products.all().order_by('-created_at')
    paginator = Paginator(products_list, 12)
    page_number = request.GET.get('page', 1)
    products = paginator.get_page(page_number)
    
    favorite_ids = set()
    if request.user.is_authenticated and request.user != shop.owner:
        favorite_ids = set(Favorite.objects.filter(user=request.user, product__shop=shop).values_list('product_id', flat=True))
    context = {
        'shop': shop,
        'products': products,
        'categories': categories,
        'news_list': news_list,
        'favorite_ids': favorite_ids,
        **cart_summary_for(request, shop),
    }
    return render(request, 'shops/front_index.html', context)

def product_detail(request, shop_slug, product_id):
    shop = get_object_or_404(Shop, slug=shop_slug)
    product = get_object_or_404(Product, id=product_id, shop=shop)
    
    favorite_ids = set()
    if request.user.is_authenticated and request.user != shop.owner:
        favorite_ids = set(Favorite.objects.filter(user=request.user, product__shop=shop).values_list('product_id', flat=True))
    context = {
        'shop': shop,
        'product': product,
        'favorite_ids': favorite_ids,
        **cart_summary_for(request, shop),
    }
    return render(request, 'shops/product_detail.html', context)

def category_products(request, shop_slug, category_id):
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
    shop = get_object_or_404(Shop, slug=shop_slug)
    news_list = shop.news.all()
    
    context = {
        'shop': shop,
        'news_list': news_list,
        'seller_shops': seller_shops_for(request.user),
        'seller_section': 'products',
    }
    return render(request, 'shops/news_list.html', context)

def news_detail(request, shop_slug, news_id):
    shop = get_object_or_404(Shop, slug=shop_slug)
    news = get_object_or_404(News, id=news_id, shop=shop)
    
    context = {
        'shop': shop,
        'news': news,
    }
    return render(request, 'shops/news_detail.html', context)

def search_products(request, shop_slug):
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


def get_or_create_cart(request, shop_slug):
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
    shop = get_object_or_404(Shop, slug=shop_slug)
    cart = get_or_create_cart(request, shop_slug)
    
    if not cart:
        return redirect('login')
    
    context = {
        'shop': shop,
        'cart': cart,
        'cart_count': cart.total_items(),
        'cart_sum': cart.total_price(),
    }
    return render(request, 'shops/cart.html', context)

@login_required
def add_to_cart(request, shop_slug, product_id):
    if request.method == 'POST':
        shop = get_object_or_404(Shop, slug=shop_slug)
        if request.user == shop.owner:
            messages.info(request, 'Владелец магазина не может покупать товары у себя. Используйте кабинет продавца.')
            return redirect('my_shops')
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
    cart = get_or_create_cart(request, shop_slug)
    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
    cart_item.delete()
    messages.success(request, 'Товар удалён из корзины')
    return redirect('cart_view', shop_slug=shop_slug)

@login_required
def update_cart_item(request, shop_slug, item_id):
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
    shop = get_object_or_404(Shop, slug=shop_slug)
    cart = get_or_create_cart(request, shop_slug)

    if cart.items.count() == 0:
        messages.error(request, 'Корзина пуста')
        return redirect('cart_view', shop_slug=shop_slug)

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()
        customer_city = request.POST.get('customer_city', '').strip() or extract_city(address)
        delivery_service = request.POST.get('delivery_service', 'courier')
        comment = request.POST.get('comment', '').strip()

        delivery_type = request.POST.get('delivery_type', 'delivery')
        if delivery_type == 'pickup':
            delivery_service = 'pickup'
            customer_city = shop.city
            address = f'Самовывоз: {shop.address or shop.city}'
        elif not all([customer_city, address]):
            messages.error(request, 'Для доставки заполните город и адрес')
            return redirect('checkout', shop_slug=shop_slug)

        if not all([full_name, phone]):
            messages.error(request, 'Заполните ФИО и телефон')
            return redirect('checkout', shop_slug=shop_slug)

        delivery_price = calculate_delivery_price(shop, customer_city, delivery_service) if shop.delivery_enabled else Decimal('0')
        order = Order.objects.create(
            user=request.user,
            shop=shop,
            full_name=full_name,
            phone=phone,
            address=address,
            customer_city=customer_city,
            delivery_service=DELIVERY_SERVICES.get(delivery_service, 'Курьер'),
            delivery_price=delivery_price,
            comment=comment,
        )

        for cart_item in cart.items.all():
            if cart_item.quantity <= cart_item.product.stock:
                OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    quantity=cart_item.quantity,
                    price=cart_item.product.price,
                )
                cart_item.product.stock -= cart_item.quantity
                cart_item.product.save()

        order.update_total()
        order.total_amount += delivery_price
        order.save(update_fields=['total_amount', 'delivery_price', 'delivery_service', 'customer_city'])
        cart.items.all().delete()

        messages.success(request, f'Заказ #{order.id} оформлен. Доставка рассчитана примерно: {delivery_price} ₽.')
        return redirect('order_confirmation', shop_slug=shop_slug, order_id=order.id)

    return render(request, 'shops/checkout.html', {
        'shop': shop,
        'cart': cart,
        'delivery_options': delivery_options_for(shop),
    })

@login_required
def order_confirmation(request, shop_slug, order_id):
    shop = get_object_or_404(Shop, slug=shop_slug)
    order = get_object_or_404(Order, id=order_id, user=request.user, shop=shop)
    
    context = {
        'shop': shop,
        'order': order,
    }
    return render(request, 'shops/order_confirmation.html', context)

@login_required
def my_orders(request, shop_slug):
    shop = get_object_or_404(Shop, slug=shop_slug)
    orders = Order.objects.filter(user=request.user, shop=shop).order_by('-created_at')
    
    context = {
        'shop': shop,
        'orders': orders,
    }
    return render(request, 'shops/my_orders.html', context)


@login_required
def add_to_favorites(request, shop_slug, product_id):
    shop = get_object_or_404(Shop, slug=shop_slug)
    if request.user == shop.owner:
        messages.info(request, 'Владелец магазина не добавляет свои товары в избранное.')
        return redirect('my_shops')
    product = get_object_or_404(Product, id=product_id, shop=shop)
    
    favorite, created = Favorite.objects.get_or_create(
        user=request.user,
        product=product
    )
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'created': created})
    if created:
        messages.success(request, f'Товар "{product.name}" добавлен в избранное')
    else:
        messages.info(request, f'Товар "{product.name}" уже в избранном')
    
    return redirect('product_detail', shop_slug=shop_slug, product_id=product_id)

@login_required
def remove_from_favorites(request, shop_slug, product_id):
    shop = get_object_or_404(Shop, slug=shop_slug)
    product = get_object_or_404(Product, id=product_id, shop=shop)
    
    Favorite.objects.filter(user=request.user, product=product).delete()
    messages.success(request, f'Товар "{product.name}" удалён из избранного')
    
    return redirect('product_detail', shop_slug=shop_slug, product_id=product_id)

@login_required
def favorites_list(request, shop_slug):
    shop = get_object_or_404(Shop, slug=shop_slug)
    favorites = Favorite.objects.filter(user=request.user, product__shop=shop)
    
    context = {
        'shop': shop,
        'favorites': favorites,
    }
    return render(request, 'shops/favorites.html', context)


@login_required
def customer_profile(request, shop_slug):
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
    
    orders = Order.objects.filter(user=request.user, shop=shop).order_by('-created_at')
    
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
    shop = get_object_or_404(Shop, slug=shop_slug)
    orders = Order.objects.filter(user=request.user, shop=shop).order_by('-created_at')
    
    context = {
        'shop': shop,
        'orders': orders,
    }
    return render(request, 'shops/customer_orders.html', context)

@login_required
def customer_order_detail(request, shop_slug, order_id):
    shop = get_object_or_404(Shop, slug=shop_slug)
    order = get_object_or_404(Order, id=order_id, user=request.user, shop=shop)
    
    context = {
        'shop': shop,
        'order': order,
    }
    return render(request, 'shops/customer_order_detail.html', context)


@login_required
def payment_page(request, shop_slug, order_id):
    shop = get_object_or_404(Shop, slug=shop_slug)
    order = get_object_or_404(Order, id=order_id, user=request.user, shop=shop)
    
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
    if request.method == 'POST':
        shop = get_object_or_404(Shop, slug=shop_slug)
        order = get_object_or_404(Order, id=order_id, user=request.user, shop=shop)
        payment = Payment.objects.get(order=order)
        
        payment_method = request.POST.get('payment_method', 'test')
        
        import uuid
        transaction_id = str(uuid.uuid4())[:8]
        
        payment.status = 'paid'
        payment.payment_method = payment_method
        payment.transaction_id = transaction_id
        payment.save()
        
        order.status = 'processing'
        order.save()
        
        messages.success(request, f'Оплата прошла успешно! Номер транзакции: {transaction_id}')
        return redirect('payment_success', shop_slug=shop_slug, order_id=order.id)
    
    return redirect('payment_page', shop_slug=shop_slug, order_id=order_id)

@login_required
def payment_success(request, shop_slug, order_id):
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
    shop = get_object_or_404(Shop, slug=shop_slug)
    order = get_object_or_404(Order, id=order_id, user=request.user, shop=shop)
    
    context = {
        'shop': shop,
        'order': order,
    }
    return render(request, 'shops/payment_failed.html', context)


def shop_customer_register(request, shop_slug):
    from django.contrib.auth import login
    from django.contrib.auth.forms import UserCreationForm
    shop = get_object_or_404(Shop, slug=shop_slug)
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            CustomerProfile.objects.get_or_create(user=user)
            login(request, user)
            messages.success(request, 'Аккаунт покупателя создан для этой витрины.')
            return redirect('shop_front', shop_slug=shop.slug)
    else:
        form = UserCreationForm()
    return render(request, 'shops/customer_register.html', {'shop': shop, 'form': form})


def shop_customer_login(request, shop_slug):
    from django.contrib.auth import login
    from django.contrib.auth.forms import AuthenticationForm
    shop = get_object_or_404(Shop, slug=shop_slug)
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect('shop_front', shop_slug=shop.slug)
    else:
        form = AuthenticationForm()
    return render(request, 'shops/customer_login.html', {'shop': shop, 'form': form})


@login_required
def download_shop_export(request, shop_slug):
    shop = get_object_or_404(Shop, slug=shop_slug, owner=request.user)
    profile, _ = SellerProfile.objects.get_or_create(user=request.user)
    if not profile.plan_config.get('download_enabled', False):
        messages.error(request, 'Скачивание сайта недоступно на тарифе Free.')
        return redirect('pricing')
    products = list(shop.products.select_related('category', 'brand').all())
    html_products = ''.join([
        f'<article><h2>{p.name}</h2><p>{p.description}</p><strong>{p.price} ₽</strong></article>'
        for p in products
    ]) or '<p>Каталог пока пуст. Добавьте товары через CRUD-кабинет.</p>'
    index_html = f'''<!doctype html>
<html lang="ru">
<head><meta charset="utf-8"><title>{shop.name}</title><style>body{{font-family:Arial;margin:40px}}article{{border:1px solid #ddd;padding:16px;margin:12px 0;border-radius:10px}}:root{{--primary:{shop.theme_color}}}</style></head>
<body><h1>{shop.name}</h1><p>{shop.description}</p><h2>Каталог</h2>{html_products}</body>
</html>'''
    products_json = json.dumps([
        {
            'name': p.name,
            'description': p.description,
            'price': str(p.price),
            'stock': p.stock,
            'category': p.category.name if p.category else '',
            'brand': p.brand.name if p.brand else '',
            'image_url': p.image_url,
        }
        for p in products
    ], ensure_ascii=False, indent=2)

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('index.html', index_html)
        archive.writestr('products.json', products_json)
        archive.writestr('README.txt', 'Статический экспорт магазина. Динамические заказы, авторизация и ИИ-помощник работают на платформе.')
    buffer.seek(0)
    response = HttpResponse(buffer.read(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{shop.slug}-export.zip"'
    return response
