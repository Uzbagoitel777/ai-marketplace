def user_roles(request):
    """Добавляет информацию о ролях пользователя в контекст"""
    context = {
        'is_super_admin': False,
        'is_seller': False,
        'is_customer': False,
    }
    
    if request.user.is_authenticated:
        context['is_super_admin'] = request.user.is_superuser
        context['is_seller'] = hasattr(request.user, 'seller_profile')
        context['is_customer'] = hasattr(request.user, 'customer_profile')
    
    return context