from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def seller_required(view_func):
    """Декоратор: доступ только для продавцов"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Необходимо войти в систему')
            return redirect('login')
        
        if not hasattr(request.user, 'seller_profile') and not request.user.is_superuser:
            messages.error(request, 'Доступ только для продавцов')
            return redirect('home')
        
        return view_func(request, *args, **kwargs)
    return wrapper

def customer_required(view_func):
    """Декоратор: доступ только для покупателей"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Необходимо войти в систему')
            return redirect('login')
        
        if not hasattr(request.user, 'customer_profile') and not request.user.is_superuser:
            messages.error(request, 'Доступ только для покупателей')
            return redirect('home')
        
        return view_func(request, *args, **kwargs)
    return wrapper

def super_admin_required(view_func):
    """Декоратор: доступ только для супер администратора"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Необходимо войти в систему')
            return redirect('login')
        
        if not request.user.is_superuser:
            messages.error(request, 'Доступ только для администратора платформы')
            return redirect('home')
        
        return view_func(request, *args, **kwargs)
    return wrapper
