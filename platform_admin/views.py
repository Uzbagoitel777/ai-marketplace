from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.db import models
from django.contrib import messages
from shops.models import Shop, Product, Order, Category, Brand
from django.utils.timezone import now
from datetime import timedelta

@staff_member_required
def admin_dashboard(request):
    """Главная панель администратора платформы"""
    
    # Общая статистика
    total_users = User.objects.count()
    total_shops = Shop.objects.count()
    total_products = Product.objects.count()
    total_orders = Order.objects.count()
    total_revenue = Order.objects.aggregate(total=models.Sum('total_amount'))['total'] or 0
    
    # Заказы по статусам
    orders_by_status = {
        'new': Order.objects.filter(status='new').count(),
        'processing': Order.objects.filter(status='processing').count(),
        'shipped': Order.objects.filter(status='shipped').count(),
        'delivered': Order.objects.filter(status='delivered').count(),
        'cancelled': Order.objects.filter(status='cancelled').count(),
    }
    
    # Заказы за последние 7 дней
    today = now().date()
    orders_by_day = []
    for i in range(7):
        day = today - timedelta(days=i)
        day_orders = Order.objects.filter(created_at__date=day).count()
        day_revenue = Order.objects.filter(created_at__date=day).aggregate(total=models.Sum('total_amount'))['total'] or 0
        orders_by_day.append({
            'date': day.strftime('%d.%m'),
            'count': day_orders,
            'revenue': float(day_revenue)
        })
    
    # Последние заказы
    recent_orders = Order.objects.all().order_by('-created_at')[:10]
    
    # Последние магазины
    recent_shops = Shop.objects.all().order_by('-created_at')[:10]
    
    # Популярные товары на платформе
    popular_products = Product.objects.filter(
        orderitem__isnull=False
    ).annotate(
        total_sold=models.Sum('orderitem__quantity')
    ).order_by('-total_sold')[:10]
    
    context = {
        'total_users': total_users,
        'total_shops': total_shops,
        'total_products': total_products,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'orders_by_status': orders_by_status,
        'orders_by_day': orders_by_day,
        'recent_orders': recent_orders,
        'recent_shops': recent_shops,
        'popular_products': popular_products,
    }
    return render(request, 'platform_admin/dashboard.html', context)

@staff_member_required
def admin_users(request):
    """Управление пользователями"""
    users = User.objects.all().order_by('-date_joined')
    
    # Поиск
    query = request.GET.get('q', '')
    if query:
        users = users.filter(username__icontains=query)
    
    context = {
        'users': users,
        'query': query,
    }
    return render(request, 'platform_admin/users.html', context)

@staff_member_required
def admin_user_detail(request, user_id):
    """Детальная страница пользователя"""
    user = User.objects.get(id=user_id)
    shops = Shop.objects.filter(owner=user)
    orders = Order.objects.filter(user=user)
    
    context = {
        'user': user,
        'shops': shops,
        'orders': orders,
    }
    return render(request, 'platform_admin/user_detail.html', context)

@staff_member_required
def admin_shops(request):
    """Управление магазинами"""
    shops = Shop.objects.all().order_by('-created_at')
    
    # Поиск
    query = request.GET.get('q', '')
    if query:
        shops = shops.filter(name__icontains=query)
    
    context = {
        'shops': shops,
        'query': query,
    }
    return render(request, 'platform_admin/shops.html', context)

@staff_member_required
def admin_orders(request):
    """Управление заказами"""
    orders = Order.objects.all().order_by('-created_at')
    
    # Фильтр по статусу
    status = request.GET.get('status', '')
    if status:
        orders = orders.filter(status=status)
    
    context = {
        'orders': orders,
        'current_status': status,
    }
    return render(request, 'platform_admin/orders.html', context)

@staff_member_required
def admin_update_order_status(request, order_id):
    """Обновление статуса заказа"""
    if request.method == 'POST':
        order = Order.objects.get(id=order_id)
        new_status = request.POST.get('status')
        order.status = new_status
        order.save()
        messages.success(request, f'Статус заказа #{order.id} изменён на {order.get_status_display()}')
    
    return redirect('admin_orders')