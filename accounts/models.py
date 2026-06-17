from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class CustomerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    phone = models.CharField(max_length=20, blank=True, verbose_name='Телефон')
    address = models.TextField(blank=True, verbose_name='Адрес доставки')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name='Аватар')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Покупатель {self.user.username}'

    class Meta:
        verbose_name = 'Профиль покупателя'
        verbose_name_plural = 'Профили покупателей'


class SellerProfile(models.Model):
    PLAN_FREE = 'free'
    PLAN_START = 'start'
    PLAN_BUSINESS = 'business'

    LEGAL_SELF = 'self_employed'
    LEGAL_IP = 'ip'
    LEGAL_OOO = 'ooo'
    LEGAL_OTHER = 'other'

    PLAN_CHOICES = [
        (PLAN_FREE, 'Free'),
        (PLAN_START, 'Start'),
        (PLAN_BUSINESS, 'Business'),
    ]

    LEGAL_FORM_CHOICES = [
        (LEGAL_SELF, 'Самозанятый'),
        (LEGAL_IP, 'ИП'),
        (LEGAL_OOO, 'ООО'),
        (LEGAL_OTHER, 'Иная форма'),
    ]

    PLAN_CONFIG = {
        PLAN_FREE: {
            'name': 'Free',
            'price': 0,
            'price_label': '0 ₽/мес',
            'shop_limit': 1,
            'ai_limit': 1,
            'ai_label': '1 демо-генерация',
            'commission': None,
            'assistant': 'Демо-помощник',
            'description': 'Пробный режим без реальных продаж: можно открыть кабинет, проверить CRUD и понять механику платформы.',
            'autofill': True,
            'demo_only': True,
            'download_enabled': False,
        },
        PLAN_START: {
            'name': 'Start',
            'price': 1490,
            'price_label': '1 490 ₽/мес',
            'shop_limit': 2,
            'ai_limit': 5,
            'ai_label': '5 разово',
            'commission': 15,
            'assistant': 'Базовый помощник покупателя',
            'description': 'До 2 магазинов, базовый шаблон, CRUD, базовый ИИ-помощник и стартовое наполнение на 12 товаров.',
            'autofill': False,
            'demo_only': False,
            'download_enabled': True,
        },
        PLAN_BUSINESS: {
            'name': 'Business',
            'price': 29900,
            'price_label': 'от 29 900 ₽/мес',
            'shop_limit': 50,
            'ai_limit': 1000000,
            'ai_label': 'неограниченно',
            'commission': 6,
            'assistant': 'Умный ИИ-помощник',
            'description': 'Кастомная платформа с расширенным ИИ, премиальным дизайном, наполнением каталога от 50 товаров и подключением интеграций.',
            'autofill': True,
            'demo_only': False,
            'download_enabled': True,
        },
    }

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='seller_profile')
    company_name = models.CharField(max_length=200, blank=True, verbose_name='Название компании')
    legal_form = models.CharField(max_length=20, choices=LEGAL_FORM_CHOICES, default=LEGAL_SELF, verbose_name='Форма деятельности')
    inn = models.CharField(max_length=20, blank=True, verbose_name='ИНН')
    ogrn = models.CharField(max_length=20, blank=True, verbose_name='ОГРН/ОГРНИП')
    legal_address = models.TextField(blank=True, verbose_name='Юридический адрес')
    contact_email = models.EmailField(blank=True, verbose_name='Рабочая почта')
    phone = models.CharField(max_length=20, blank=True, verbose_name='Телефон')
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default=PLAN_FREE, verbose_name='Тариф')
    ai_generations_used = models.PositiveIntegerField(default=0, verbose_name='Использовано ИИ-генераций')
    is_approved = models.BooleanField(default=True, verbose_name='Подтверждён')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def plan_config(self):
        return self.PLAN_CONFIG.get(self.plan, self.PLAN_CONFIG[self.PLAN_FREE])

    @property
    def monthly_fee(self):
        return int(self.plan_config['price'])

    @property
    def shop_limit(self):
        return self.plan_config['shop_limit']

    @property
    def ai_limit(self):
        return self.plan_config['ai_limit']

    @property
    def commission_percent(self):
        return self.plan_config['commission']

    @property
    def shops_used(self):
        return self.user.shops.count()

    @property
    def can_create_shop(self):
        return self.shops_used < self.shop_limit

    @classmethod
    def plans_for_template(cls):
        return [{'code': code, **cfg} for code, cfg in cls.PLAN_CONFIG.items()]

    def __str__(self):
        return f'{self.user.username} — {self.plan_config["name"]}'

    class Meta:
        verbose_name = 'Профиль продавца'
        verbose_name_plural = 'Профили продавцов'


class PlatformReview(models.Model):
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='platform_reviews')
    company_name = models.CharField(max_length=200, blank=True, verbose_name='Компания')
    rating = models.PositiveSmallIntegerField(default=5, verbose_name='Оценка')
    text = models.TextField(verbose_name='Отзыв')
    is_public = models.BooleanField(default=True, verbose_name='Показывать на сайте')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.company_name or self.seller.username}: {self.rating}/5'

    class Meta:
        verbose_name = 'Отзыв о платформе'
        verbose_name_plural = 'Отзывы о платформе'
        ordering = ['-created_at']


@receiver(post_save, sender=User)
def create_user_profiles(sender, instance, created, **kwargs):
    if created:
        CustomerProfile.objects.get_or_create(user=instance)
