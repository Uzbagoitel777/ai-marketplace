# Generated manually for seller cabinet delivery/payment settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('shops', '0007_order_customer_city_order_delivery_price_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='PaymentAccount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('recipient_name', models.CharField(blank=True, max_length=200, verbose_name='Получатель')),
                ('bank_name', models.CharField(blank=True, max_length=160, verbose_name='Банк')),
                ('account_number', models.CharField(blank=True, max_length=40, verbose_name='Расчетный счет')),
                ('bik', models.CharField(blank=True, max_length=20, verbose_name='БИК')),
                ('inn', models.CharField(blank=True, max_length=20, verbose_name='ИНН получателя')),
                ('payment_comment', models.CharField(blank=True, max_length=250, verbose_name='Комментарий')),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('shop', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='payment_account', to='shops.shop')),
            ],
            options={
                'verbose_name': 'Счет для выплат',
                'verbose_name_plural': 'Счета для выплат',
            },
        ),
        migrations.CreateModel(
            name='Warehouse',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120, verbose_name='Название склада/магазина')),
                ('city', models.CharField(max_length=100, verbose_name='Город')),
                ('address', models.CharField(max_length=250, verbose_name='Адрес')),
                ('delivery_services', models.CharField(default='Самовывоз, Курьер, СДЭК', max_length=250, verbose_name='Службы доставки')),
                ('is_pickup_point', models.BooleanField(default=True, verbose_name='Доступен самовывоз')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('shop', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='warehouses', to='shops.shop')),
            ],
            options={
                'verbose_name': 'Склад/магазин',
                'verbose_name_plural': 'Склады/магазины',
            },
        ),
    ]
