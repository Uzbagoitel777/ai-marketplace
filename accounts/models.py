from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class CustomerProfile(models.Model):
    """Профиль покупателя"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    phone = models.CharField(max_length=20, blank=True, verbose_name='Телефон')
    address = models.TextField(blank=True, verbose_name='Адрес доставки')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name='Аватар')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Профиль {self.user.username}"
    
    class Meta:
        verbose_name = 'Профиль покупателя'
        verbose_name_plural = 'Профили покупателей'


class SellerProfile(models.Model):
    """Профиль продавца (администратор магазина)"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='seller_profile')
    company_name = models.CharField(max_length=200, blank=True, verbose_name='Название компании')
    phone = models.CharField(max_length=20, blank=True, verbose_name='Телефон')
    is_approved = models.BooleanField(default=True, verbose_name='Подтверждён')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Продавец: {self.user.username}"
    
    class Meta:
        verbose_name = 'Профиль продавца'
        verbose_name_plural = 'Профили продавцов'


@receiver(post_save, sender=User)
def create_user_profiles(sender, instance, created, **kwargs):
    """Автоматическое создание профилей при регистрации"""
    if created:
        # По умолчанию все новые пользователи - покупатели
        CustomerProfile.objects.get_or_create(user=instance)