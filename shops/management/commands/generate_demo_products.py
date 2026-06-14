from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from shops.models import Shop, Category, Product, Brand
import random

class Command(BaseCommand):
    help = 'Генерирует тестовые товары для магазина'

    def add_arguments(self, parser):
        parser.add_argument('shop_slug', type=str, help='Slug магазина')
        parser.add_argument('--count', type=int, default=20, help='Количество товаров')

    def handle(self, *args, **options):
        shop_slug = options['shop_slug']
        count = options['count']
        
        try:
            shop = Shop.objects.get(slug=shop_slug)
        except Shop.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Магазин с slug "{shop_slug}" не найден'))
            return
        
        categories = list(shop.categories.all())
        if not categories:
            self.stdout.write(self.style.WARNING('В магазине нет категорий. Создайте хотя бы одну категорию.'))
            return
        
        # Создаем бренды для магазина, если их нет
        brand_names = ['Samsung', 'Apple', 'Xiaomi', 'Huawei', 'Sony', 'LG', 'HP', 'Dell', 'Asus', 'Acer']
        brands = []
        for brand_name in brand_names:
            brand, created = Brand.objects.get_or_create(
                shop=shop,
                name=brand_name,
                defaults={'description': f'Бренд {brand_name}'}
            )
            brands.append(brand)
        
        # Списки для генерации
        product_names = [
            'Смартфон', 'Ноутбук', 'Наушники', 'Клавиатура', 'Мышь', 'Монитор', 
            'Чехол для телефона', 'Зарядное устройство', 'Внешний аккумулятор', 
            'Смарт-часы', 'Фитнес-браслет', 'Планшет', 'Колонка', 'Микрофон',
            'Веб-камера', 'Роутер', 'Внешний жесткий диск', 'Флешка', 'Джойстик',
            'Коврик для мыши', 'Подставка для ноутбука', 'Сумка для ноутбука'
        ]
        
        descriptions = [
            'Отличное качество по доступной цене. Подходит для повседневного использования.',
            'Современная модель с расширенными функциями. Идеально для работы и развлечений.',
            'Проверенный временем товар. Положительные отзывы от покупателей.',
            'Новинка этого сезона. Успейте приобрести по выгодной цене.',
            'Профессиональное устройство для требовательных пользователей.',
            'Компактный и удобный. Отлично подходит для путешествий.',
            'Энергоэффективный товар с длительным сроком службы.',
            'Стильный дизайн и высокая производительность.'
        ]
        
        created_count = 0
        
        for i in range(count):
            name = random.choice(product_names) + f' {random.randint(1, 100)}'
            category = random.choice(categories)
            brand = random.choice(brands)
            price = random.randint(500, 50000)
            stock = random.randint(0, 100)
            description = random.choice(descriptions)
            
            product = Product.objects.create(
                shop=shop,
                name=name,
                category=category,
                brand=brand,
                price=price,
                stock=stock,
                description=description
            )
            created_count += 1
            self.stdout.write(f'Создан товар: {product.name}')
        
        self.stdout.write(self.style.SUCCESS(f'Успешно создано {created_count} товаров для магазина "{shop.name}"'))