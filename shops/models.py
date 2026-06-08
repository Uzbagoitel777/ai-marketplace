from django.db import models
from django.contrib.auth.models import User

class Shop(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shops')
    name = models.CharField(max_length=100, verbose_name='Название магазина')
    slug = models.SlugField(unique=True, verbose_name='URL-адрес')
    description = models.TextField(blank=True, verbose_name='Описание')
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