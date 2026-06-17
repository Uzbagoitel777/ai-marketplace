from django.db import models
from django.contrib.auth.models import User

class Shop(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shops')
    name = models.CharField(max_length=100, verbose_name='Название магазина')
    slug = models.SlugField(unique=True, verbose_name='URL-адрес')
    description = models.TextField(blank=True, verbose_name='Описание')
    custom_css = models.TextField(blank=True, null=True, verbose_name='Кастомный CSS')
    template_key = models.CharField(max_length=40, default='modern', verbose_name='Базовый шаблон')
    is_demo = models.BooleanField(default=False, verbose_name='Демо-магазин')
    assistant_level = models.CharField(max_length=20, default='basic', verbose_name='Уровень ИИ-помощника')
    city = models.CharField(max_length=100, default='Екатеринбург', verbose_name='Город магазина')
    address = models.CharField(max_length=250, blank=True, verbose_name='Адрес магазина')
    hosting_enabled = models.BooleanField(default=False, verbose_name='Хостинг на платформе')
    theme_color = models.CharField(max_length=20, default='#4361ee', verbose_name='Цвет темы')
    delivery_enabled = models.BooleanField(default=True, verbose_name='Доставка включена')
    delivery_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Стоимость доставки')
    delivery_description = models.TextField(blank=True, default='Доставка рассчитывается при оформлении заказа', verbose_name='Описание доставки')
    payment_enabled = models.BooleanField(default=True, verbose_name='Оплата включена')
    payment_methods = models.CharField(max_length=200, default='Банковская карта, оплата при получении', verbose_name='Способы оплаты')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = 'Магазин'
        verbose_name_plural = 'Магазины'

class Category(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=100, verbose_name='Название категории')
    order = models.IntegerField(default=0, verbose_name='Порядок')
    
    def __str__(self):
        return f'{self.name} ({self.shop.name})'
    
    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['order']

class Brand(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='brands')
    name = models.CharField(max_length=100, verbose_name='Название бренда')
    description = models.TextField(blank=True, verbose_name='Описание')
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = 'Бренд'
        verbose_name_plural = 'Бренды'

class Product(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    name = models.CharField(max_length=200, verbose_name='Название товара')
    description = models.TextField(verbose_name='Описание')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена')
    stock = models.IntegerField(default=0, verbose_name='Количество на складе')
    image = models.ImageField(upload_to='products/', blank=True, null=True, verbose_name='Изображение')
    image_url = models.URLField(blank=True, verbose_name='Ссылка на изображение')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата добавления')
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'

class News(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='news')
    title = models.CharField(max_length=200, verbose_name='Заголовок')
    content = models.TextField(verbose_name='Содержание')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата публикации')
    
    def __str__(self):
        return self.title
    
    class Meta:
        verbose_name = 'Новость'
        verbose_name_plural = 'Новости'
        ordering = ['-created_at']


class Warehouse(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='warehouses')
    name = models.CharField(max_length=120, verbose_name='Название склада/магазина')
    city = models.CharField(max_length=100, verbose_name='Город')
    address = models.CharField(max_length=250, verbose_name='Адрес')
    delivery_services = models.CharField(max_length=250, default='Самовывоз, Курьер, СДЭК', verbose_name='Службы доставки')
    is_pickup_point = models.BooleanField(default=True, verbose_name='Доступен самовывоз')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.name} — {self.city}'

    class Meta:
        verbose_name = 'Склад/магазин'
        verbose_name_plural = 'Склады/магазины'


class PaymentAccount(models.Model):
    shop = models.OneToOneField(Shop, on_delete=models.CASCADE, related_name='payment_account')
    recipient_name = models.CharField(max_length=200, blank=True, verbose_name='Получатель')
    bank_name = models.CharField(max_length=160, blank=True, verbose_name='Банк')
    account_number = models.CharField(max_length=40, blank=True, verbose_name='Расчетный счет')
    bik = models.CharField(max_length=20, blank=True, verbose_name='БИК')
    inn = models.CharField(max_length=20, blank=True, verbose_name='ИНН получателя')
    payment_comment = models.CharField(max_length=250, blank=True, verbose_name='Комментарий')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.recipient_name or f'Счет магазина {self.shop.name}'

    class Meta:
        verbose_name = 'Счет для выплат'
        verbose_name_plural = 'Счета для выплат'


class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='carts')
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='carts')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Корзина {self.user.username} - {self.shop.name}"
    
    def total_price(self):
        return sum(item.total_price() for item in self.items.all())
    
    def total_items(self):
        return sum(item.quantity for item in self.items.all())
    
    class Meta:
        verbose_name = 'Корзина'
        verbose_name_plural = 'Корзины'

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    
    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
    
    def total_price(self):
        return self.product.price * self.quantity
    
    class Meta:
        verbose_name = 'Товар в корзине'
        verbose_name_plural = 'Товары в корзине'

class Order(models.Model):
    STATUS_CHOICES = [
        ('new', 'Новый'),
        ('processing', 'В обработке'),
        ('shipped', 'Отправлен'),
        ('delivered', 'Доставлен'),
        ('cancelled', 'Отменён'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='orders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    full_name = models.CharField(max_length=200, verbose_name='ФИО')
    phone = models.CharField(max_length=20, verbose_name='Телефон')
    address = models.TextField(verbose_name='Адрес доставки')
    comment = models.TextField(blank=True, verbose_name='Комментарий')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', verbose_name='Статус')
    delivery_service = models.CharField(max_length=50, blank=True, verbose_name='Служба доставки')
    delivery_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Стоимость доставки')
    customer_city = models.CharField(max_length=100, blank=True, verbose_name='Город клиента')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Общая сумма')
    
    def __str__(self):
        return f"Заказ #{self.id} - {self.user.username}"
    
    def update_total(self):
        total = sum(item.total_price() for item in self.items.all())
        self.total_amount = total
        self.save(update_fields=['total_amount'])
    
    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-created_at']

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
    
    def total_price(self):
        return self.price * self.quantity
    
    class Meta:
        verbose_name = 'Товар в заказе'
        verbose_name_plural = 'Товары в заказе'

class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'product']
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'
    
    def __str__(self):
        return f"{self.user.username} - {self.product.name}"

class Payment(models.Model):
    PAYMENT_STATUS = [
        ('pending', 'Ожидает оплаты'),
        ('paid', 'Оплачен'),
        ('failed', 'Ошибка'),
        ('refunded', 'Возврат'),
    ]
    
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Сумма')
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending', verbose_name='Статус')
    payment_method = models.CharField(max_length=50, blank=True, verbose_name='Способ оплаты')
    transaction_id = models.CharField(max_length=100, blank=True, verbose_name='ID транзакции')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Платеж для заказа #{self.order.id} - {self.status}"
    
    class Meta:
        verbose_name = 'Платеж'
        verbose_name_plural = 'Платежи'
