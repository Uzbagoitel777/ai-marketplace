import json
import re
import time
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils.text import slugify

from .services.hf_inference import HuggingFaceInference
from accounts.models import SellerProfile
from shops.models import Brand, Cart, CartItem, Category, Favorite, News, Product, Shop, Warehouse, PaymentAccount


def init_ai():
    return HuggingFaceInference()


def _unique_slug(name, user_id):
    slug = slugify(name)
    if not slug:
        slug = f"shop-{user_id}-{int(time.time())}"

    original_slug = slug
    counter = 1
    while Shop.objects.filter(slug=slug).exists():
        slug = f"{original_slug}-{counter}"
        counter += 1
    return slug


@login_required
def ai_create_shop(request):
    if request.method == 'POST':
        shop_name = request.POST.get('shop_name', '').strip()
        shop_description = request.POST.get('shop_description', '').strip()
        template_key = request.POST.get('template_key', 'modern')
        city = request.POST.get('city', '').strip()
        address = request.POST.get('address', '').strip()
        favorite_color = request.POST.get('favorite_color', '').strip()
        design_notes = request.POST.get('design_notes', '').strip()
        revision_request = request.POST.get('revision_request', '').strip()
        try:
            product_count = max(1, min(50, int(request.POST.get('product_count', '12'))))
        except (TypeError, ValueError):
            product_count = 12

        if not shop_name:
            messages.error(request, 'Введите название магазина')
            return redirect('ai_create_shop')
        if not city or not address:
            messages.error(request, 'Укажите город и адрес нахождения магазина')
            return redirect('ai_create_shop')

        profile, _ = SellerProfile.objects.get_or_create(user=request.user)
        if not profile.can_create_shop:
            messages.error(request, f'На тарифе {profile.plan_config["name"]} можно создать максимум {profile.shop_limit} магазин(ов). Выберите тариф выше.')
            return redirect('pricing')

        ai = init_ai()
        bundle = ai.generate_storefront_bundle(shop_name, shop_description, profile.plan, template_key, city=city, address=address, favorite_color=favorite_color, design_notes=design_notes, revision_request=revision_request, requested_product_count=product_count)
        bundle['requested_product_count'] = product_count
        bundle['products'] = bundle.get('products', [])[:product_count]
        profile.ai_generations_used += 1
        profile.save(update_fields=['ai_generations_used', 'updated_at'])
        request.session['ai_shop_data'] = bundle

        return render(request, 'ai_assistant/confirm_shop.html', {
            'shop_name': bundle['name'],
            'generated_description': bundle['description'],
            'categories': bundle['categories'],
            'products': bundle['products'],
            'news': bundle['news'],
            'delivery': bundle['delivery'],
            'payment': bundle['payment'],
            'custom_css': bundle['custom_css'],
            'plan_name': profile.plan_config['name'],
            'template_key': bundle.get('template_key', template_key),
            'autofill': profile.plan_config.get('autofill', True),
            'requested_product_count': product_count,
            'original_description': shop_description,
            'favorite_color': favorite_color or bundle.get('theme_color', '#4361ee'),
            'design_notes': design_notes,
            'city': city,
            'address': address,
            'seller_shops': request.user.shops.all().order_by('-created_at'),
            'seller_section': 'products',
        })

    return render(request, 'ai_assistant/create_shop_ai.html', {'seller_shops': request.user.shops.all().order_by('-created_at'), 'seller_section': 'products'})


@login_required
def confirm_create_shop(request):
    if request.method != 'POST':
        return redirect('ai_create_shop')

    shop_data = request.session.get('ai_shop_data')
    if not shop_data:
        messages.error(request, 'Данные не найдены, начните заново')
        return redirect('ai_create_shop')

    with transaction.atomic():
        profile, _ = SellerProfile.objects.get_or_create(user=request.user)
        if not profile.can_create_shop:
            messages.error(request, f'Лимит магазинов по тарифу {profile.plan_config["name"]} исчерпан.')
            return redirect('pricing')
        slug = _unique_slug(shop_data['name'], request.user.id)
        delivery = shop_data.get('delivery', {})
        payment = shop_data.get('payment', {})
        plan_code = shop_data.get('plan_code', profile.plan)

        shop = Shop.objects.create(
            owner=request.user,
            name=shop_data['name'],
            slug=slug,
            description=shop_data.get('description', ''),
            theme_color=shop_data.get('theme_color', '#4361ee'),
            custom_css=shop_data.get('custom_css', ''),
            template_key=shop_data.get('template_key', 'modern'),
            is_demo=plan_code == SellerProfile.PLAN_FREE,
            assistant_level='smart' if plan_code == SellerProfile.PLAN_BUSINESS else 'basic',
            city=shop_data.get('city', 'Екатеринбург'),
            address=shop_data.get('address', ''),
            hosting_enabled=plan_code == SellerProfile.PLAN_BUSINESS,
            delivery_enabled=delivery.get('enabled', True),
            delivery_price=Decimal(str(delivery.get('price', '0'))),
            delivery_description=delivery.get('description', ''),
            payment_enabled=payment.get('enabled', True),
            payment_methods=payment.get('methods', 'Банковская карта, оплата при получении'),
        )

        Warehouse.objects.create(
            shop=shop,
            name='Главный магазин',
            city=shop.city,
            address=shop.address or shop.city,
            delivery_services='Самовывоз, Курьер, СДЭК',
            is_pickup_point=True,
        )
        PaymentAccount.objects.get_or_create(shop=shop)

        categories_by_name = {}
        for index, category_name in enumerate(shop_data.get('categories', [])[:8], start=1):
            if category_name and len(category_name) <= 100:
                category, _ = Category.objects.get_or_create(shop=shop, name=category_name, defaults={'order': index})
                categories_by_name[category.name] = category

        brand_name = 'AI Market'
        first_product = next(iter(shop_data.get('products', [])), None)
        if first_product:
            brand_name = first_product.get('brand') or brand_name
        brand, _ = Brand.objects.get_or_create(shop=shop, name=brand_name, defaults={'description': 'Бренд создан ИИ для стартовой витрины'})

        fallback_category = next(iter(categories_by_name.values()), None)
        for product_data in shop_data.get('products', []):
            category = categories_by_name.get(product_data.get('category')) or fallback_category
            Product.objects.create(
                shop=shop,
                category=category,
                brand=brand,
                name=product_data.get('name', 'Товар'),
                description=product_data.get('description', ''),
                price=Decimal(str(product_data.get('price', '0'))),
                stock=int(product_data.get('stock', 0)),
                image_url=product_data.get('image_url', ''),
            )

        for news_data in shop_data.get('news', [])[:3]:
            News.objects.create(
                shop=shop,
                title=news_data.get('title', 'Новость магазина'),
                content=news_data.get('content', ''),
            )

    request.session.pop('ai_shop_data', None)
    messages.success(request, f'Магазин «{shop.name}» создан полностью: витрина, категории, товары, новости, доставка и оплата готовы.')
    return redirect('shop_dashboard', shop_slug=shop.slug)


@login_required
def generate_product_description_ajax(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request'}, status=400)

    try:
        data = json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    product_name = data.get('product_name', '').strip()
    category_name = data.get('category_name', '').strip()

    if not product_name:
        return JsonResponse({'error': 'product_name is required'}, status=400)

    ai = init_ai()
    description = ai.generate_product_description(product_name, category_name)
    return JsonResponse({'description': description})


def _find_product_by_question(products, question):
    q = (question or '').lower()
    normalized_q = re.sub(r'[^a-zа-яё0-9\s]', ' ', q)
    tokens = {token for token in normalized_q.split() if len(token) >= 3}

    best_product = None
    best_score = 0
    for product in products:
        haystack = f"{product.name} {product.description} {product.category.name if product.category else ''}".lower()
        score = sum(1 for token in tokens if token in haystack)
        if product.name.lower() in q:
            score += 5
        if score > best_score:
            best_score = score
            best_product = product

    return best_product if best_score > 0 else None


def ai_chat(request, shop_slug):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request'}, status=400)

    try:
        data = json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError:
        return JsonResponse({'answer': 'Не понял запрос. Попробуйте написать проще.'}, status=400)

    question = data.get('question', '').strip()
    if not question:
        return JsonResponse({'answer': 'Напишите вопрос о товаре, доставке или оплате.'})

    try:
        shop = Shop.objects.get(slug=shop_slug)
    except Shop.DoesNotExist:
        return JsonResponse({'answer': 'Магазин не найден.'}, status=404)

    products = list(shop.products.select_related('category').all()[:50])
    products_info = "\n".join([
        f"- {p.name}: {p.price} руб. (в наличии: {p.stock} шт.; категория: {p.category.name if p.category else 'без категории'})"
        for p in products
    ]) or 'В магазине пока нет товаров'

    q_lower = question.lower()
    add_intent = any(word in q_lower for word in ['добавь', 'добавить', 'закинь', 'положи', 'корзин'])
    favorite_intent = any(word in q_lower for word in ['избран', 'сохрани', 'отложи', 'лайк'])
    matched_product = _find_product_by_question(products, question)

    if shop.assistant_level == 'basic' and not add_intent and not favorite_intent:
        if any(word in q_lower for word in ['достав', 'получ', 'сдэк', 'самовывоз']):
            return JsonResponse({'answer': f'Магазин находится: {shop.city}, {shop.address or "адрес уточняется"}. При оформлении можно выбрать самовывоз или доставку, стоимость считается примерно по городу клиента и службе доставки.'})
        if any(word in q_lower for word in ['оплат', 'карт', 'сбп', 'налич']):
            return JsonResponse({'answer': 'Оплату можно пройти в тестовом режиме: карта, СБП или оплата при получении. После заказа откроется форма с демо-вводом карты.'})
        if matched_product:
            return JsonResponse({'answer': f'Подходит «{matched_product.name}» за {matched_product.price} ₽. В наличии {matched_product.stock} шт. Напишите «добавь {matched_product.name} в корзину» или «сохрани {matched_product.name} в избранное».'})
        if products:
            cheapest = sorted(products, key=lambda p: p.price)[0]
            return JsonResponse({'answer': f'По вашему запросу точного совпадения нет, но могу предложить бюджетный вариант: «{cheapest.name}» за {cheapest.price} ₽. Еще можно написать категорию или конкретное название товара.'})
        return JsonResponse({'answer': 'Каталог пока пустой. Продавец может добавить товары через кнопку «Редактировать товары» в шапке магазина.'})

    if favorite_intent:
        if request.user.is_authenticated and request.user == shop.owner:
            return JsonResponse({'answer': 'Вы владелец этого магазина. Покупательские действия для своих товаров отключены.'})
        if not matched_product:
            return JsonResponse({'answer': 'Я не нашел подходящий товар. Напишите точнее название.'})
        if not request.user.is_authenticated:
            return JsonResponse({'answer': f'Я нашел «{matched_product.name}», но для избранного нужно войти как покупатель на этой витрине.'})
        Favorite.objects.get_or_create(user=request.user, product=matched_product)
        return JsonResponse({'answer': f'Готово: «{matched_product.name}» добавлен в избранное.'})

    if add_intent:
        if request.user.is_authenticated and request.user == shop.owner:
            return JsonResponse({'answer': 'Вы владелец этого магазина. Добавление своих товаров в корзину отключено.'})
        if not matched_product:
            return JsonResponse({'answer': 'Я не нашел подходящий товар в каталоге. Напишите точнее название товара.'})
        if matched_product.stock <= 0:
            return JsonResponse({'answer': f'Товар «{matched_product.name}» сейчас закончился.'})
        if not request.user.is_authenticated:
            return JsonResponse({'answer': f'Я нашел «{matched_product.name}», но для добавления в корзину нужно войти как покупатель на этой витрине.'})

        cart, _ = Cart.objects.get_or_create(user=request.user, shop=shop)
        item, created = CartItem.objects.get_or_create(cart=cart, product=matched_product, defaults={'quantity': 1})
        if not created and item.quantity < matched_product.stock:
            item.quantity += 1
            item.save(update_fields=['quantity'])

        return JsonResponse({
            'answer': f'Готово: «{matched_product.name}» добавлен в корзину. В корзине сейчас {cart.total_items()} товар(ов) на сумму {cart.total_price()} ₽.',
            'cart_total': cart.total_items(),
        })

    ai = init_ai()
    answer = ai.chat_with_customer(question, products_info)
    if matched_product and any(word in question.lower() for word in ['посовет', 'подбери', 'нужен', 'хочу', 'ищу', 'выбери']):
        answer += f' Конкретно под ваш запрос подходит «{matched_product.name}» за {matched_product.price} ₽. Чтобы добавить его, напишите: “добавь {matched_product.name} в корзину”.'

    return JsonResponse({'answer': answer})
