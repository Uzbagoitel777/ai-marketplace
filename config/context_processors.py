def user_roles(request):
    """Добавляет роли пользователя и активный магазин в контекст шаблонов."""
    context = {
        'is_super_admin': False,
        'is_seller': False,
        'is_customer': False,
        'active_shop_slug': None,
    }
    
    try:
        if getattr(request, 'resolver_match', None):
            context['active_shop_slug'] = request.resolver_match.kwargs.get('shop_slug')
    except Exception:
        context['active_shop_slug'] = None

    if request.user.is_authenticated:
        context['is_super_admin'] = request.user.is_superuser
        context['is_seller'] = hasattr(request.user, 'seller_profile')
        context['is_customer'] = hasattr(request.user, 'customer_profile')

        if not context['active_shop_slug']:
            try:
                from shops.models import Shop
                owned_shop = Shop.objects.filter(owner=request.user).order_by('-created_at').first()
                any_shop = owned_shop or Shop.objects.order_by('-created_at').first()
                context['active_shop_slug'] = any_shop.slug if any_shop else None
            except Exception:
                context['active_shop_slug'] = None

    return context
