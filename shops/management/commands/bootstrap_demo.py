from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import CustomerProfile, SellerProfile
from ai_assistant.services.hf_inference import HuggingFaceInference
from ai_assistant.views import _unique_slug
from shops.models import Brand, Category, News, Order, OrderItem, Payment, Product, Shop, Warehouse, PaymentAccount


class Command(BaseCommand):
    help = 'Создает демо-пользователей и готовую ИИ-витрину для защиты проекта.'

    def add_arguments(self, parser):
        parser.add_argument('--shop-name', default='Demo Tech Store')
        parser.add_argument('--description', default='электроника, смартфоны, ноутбуки и аксессуары')

    def handle(self, *args, **options):
        admin, _ = User.objects.get_or_create(username='admin')
        admin.is_staff = True
        admin.is_superuser = True
        admin.set_password('admin12345')
        admin.save()

        seller, _ = User.objects.get_or_create(username='seller')
        seller.set_password('seller12345')
        seller.save()
        CustomerProfile.objects.get_or_create(user=seller)
        SellerProfile.objects.update_or_create(user=seller, defaults={'company_name': 'Demo Seller', 'legal_form': SellerProfile.LEGAL_IP, 'inn': '667100000000', 'ogrn': '326665800000000', 'legal_address': 'Екатеринбург, проспект Ленина, 1', 'contact_email': 'seller@example.ru', 'phone': '+7 900 000-00-00', 'plan': SellerProfile.PLAN_BUSINESS, 'ai_generations_used': 12})

        customer, _ = User.objects.get_or_create(username='customer')
        customer.set_password('customer12345')
        customer.save()
        CustomerProfile.objects.get_or_create(user=customer)

        ai = HuggingFaceInference()
        bundle = ai.generate_storefront_bundle(options['shop_name'], options['description'], SellerProfile.PLAN_BUSINESS, 'premium', city='Екатеринбург', address='проспект Ленина, 1', use_ai=False)
        slug = _unique_slug(bundle['name'], seller.id)
        shop = Shop.objects.create(
            owner=seller,
            name=bundle['name'],
            slug=slug,
            description=bundle['description'],
            theme_color=bundle['theme_color'],
            custom_css=bundle['custom_css'],
            template_key=bundle.get('template_key', 'premium'),
            assistant_level='smart',
            city=bundle.get('city', 'Екатеринбург'),
            address=bundle.get('address', 'проспект Ленина, 1'),
            hosting_enabled=True,
            delivery_enabled=bundle['delivery']['enabled'],
            delivery_price=bundle['delivery']['price'],
            delivery_description=bundle['delivery']['description'],
            payment_enabled=bundle['payment']['enabled'],
            payment_methods=bundle['payment']['methods'],
        )

        Warehouse.objects.create(
            shop=shop,
            name='Главный магазин',
            city=shop.city,
            address=shop.address or 'проспект Ленина, 1',
            delivery_services='Самовывоз, Курьер, СДЭК, Почта России',
            is_pickup_point=True,
        )
        Warehouse.objects.create(
            shop=shop,
            name='Склад FBS',
            city='Екатеринбург',
            address='улица Малышева, 10',
            delivery_services='Курьер, СДЭК',
            is_pickup_point=False,
        )
        PaymentAccount.objects.create(
            shop=shop,
            recipient_name='ИП Demo Seller',
            bank_name='Тестовый банк',
            account_number='40702810000000000000',
            bik='044525000',
            inn='667100000000',
            payment_comment='Демо-счет для презентации',
        )

        categories = {}
        for i, category_name in enumerate(bundle['categories'], start=1):
            categories[category_name] = Category.objects.create(shop=shop, name=category_name, order=i)

        brand_name = bundle['products'][0]['brand'] if bundle['products'] else 'AI Market'
        brand = Brand.objects.create(shop=shop, name=brand_name, description='Демо-бренд для защиты проекта')

        fallback_category = next(iter(categories.values()))
        for product in bundle['products']:
            Product.objects.create(
                shop=shop,
                category=categories.get(product['category'], fallback_category),
                brand=brand,
                name=product['name'],
                description=product['description'],
                price=product['price'],
                stock=product['stock'],
                image_url=product.get('image_url', ''),
            )

        for news in bundle['news']:
            News.objects.create(shop=shop, title=news['title'], content=news['content'])

        demo_products = list(shop.products.all()[:8])
        for index in range(1, 7):
            order = Order.objects.create(
                user=customer,
                shop=shop,
                full_name='Демо Покупатель',
                phone='+7 900 111-22-33',
                address='Екатеринбург, улица Малышева, 10',
                customer_city='Екатеринбург',
                delivery_service='Курьер по городу',
                delivery_price=Decimal('250'),
                status=['new', 'processing', 'shipped', 'delivered', 'delivered', 'cancelled'][index - 1],
            )
            for product in demo_products[index % len(demo_products):(index % len(demo_products)) + 2]:
                OrderItem.objects.create(order=order, product=product, quantity=1 + index % 2, price=product.price)
            order.update_total()
            order.total_amount += order.delivery_price
            order.created_at = timezone.now() - timedelta(days=6-index)
            order.save(update_fields=['total_amount', 'created_at'])
            Payment.objects.create(order=order, amount=order.total_amount, status='paid' if order.status != 'cancelled' else 'failed', payment_method='demo-card', transaction_id=f'DEMO{index:04d}')

        self.stdout.write(self.style.SUCCESS('Демо-данные созданы.'))
        self.stdout.write(f'Админ: admin / admin12345')
        self.stdout.write(f'Продавец: seller / seller12345')
        self.stdout.write(f'Покупатель: customer / customer12345')
        self.stdout.write(f'Витрина: /shops/{shop.slug}/')
