# Generated for project completion: storefront theme, delivery and payment settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shops', '0005_shop_custom_css'),
    ]

    operations = [
        migrations.AddField(
            model_name='shop',
            name='theme_color',
            field=models.CharField(default='#4361ee', max_length=20, verbose_name='Цвет темы'),
        ),
        migrations.AddField(
            model_name='shop',
            name='delivery_enabled',
            field=models.BooleanField(default=True, verbose_name='Доставка включена'),
        ),
        migrations.AddField(
            model_name='shop',
            name='delivery_price',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='Стоимость доставки'),
        ),
        migrations.AddField(
            model_name='shop',
            name='delivery_description',
            field=models.TextField(blank=True, default='Доставка рассчитывается при оформлении заказа', verbose_name='Описание доставки'),
        ),
        migrations.AddField(
            model_name='shop',
            name='payment_enabled',
            field=models.BooleanField(default=True, verbose_name='Оплата включена'),
        ),
        migrations.AddField(
            model_name='shop',
            name='payment_methods',
            field=models.CharField(default='Банковская карта, оплата при получении', max_length=200, verbose_name='Способы оплаты'),
        ),
    ]
