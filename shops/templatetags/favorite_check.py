from django import template
from shops.models import Favorite

register = template.Library()

@register.filter(name='is_favorite')
def is_favorite(product, user):
    if user.is_authenticated:
        return Favorite.objects.filter(user=user, product=product).exists()
    return False