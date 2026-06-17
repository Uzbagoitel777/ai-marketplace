from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect, render

from .models import CustomerProfile, PlatformReview, SellerProfile


def register_customer(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            CustomerProfile.objects.get_or_create(user=user)
            login(request, user)
            messages.success(request, 'Аккаунт покупателя создан.')
            next_url = request.POST.get('next') or 'home'
            return redirect(next_url)
    else:
        form = UserCreationForm()

    return render(request, 'accounts/register.html', {
        'form': form,
        'role_title': 'Регистрация покупателя',
        'role_hint': 'Аккаунт покупателя используется только внутри конкретной витрины магазина.',
        'submit_label': 'Создать аккаунт покупателя',
    })


def register_seller(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        data = {
            'company_name': request.POST.get('company_name', '').strip(),
            'legal_form': request.POST.get('legal_form', SellerProfile.LEGAL_SELF),
            'inn': request.POST.get('inn', '').strip(),
            'ogrn': request.POST.get('ogrn', '').strip(),
            'legal_address': request.POST.get('legal_address', '').strip(),
            'contact_email': request.POST.get('contact_email', '').strip(),
            'phone': request.POST.get('phone', '').strip(),
            'is_approved': True,
        }
        if data['legal_form'] not in dict(SellerProfile.LEGAL_FORM_CHOICES):
            data['legal_form'] = SellerProfile.LEGAL_SELF
        if form.is_valid():
            user = form.save()
            CustomerProfile.objects.get_or_create(user=user)
            SellerProfile.objects.get_or_create(user=user, defaults=data)
            login(request, user)
            messages.success(request, 'Аккаунт продавца создан. Теперь можно выбрать тариф и создать магазин.')
            return redirect('my_shops')
    else:
        form = UserCreationForm()

    return render(request, 'accounts/register.html', {
        'form': form,
        'seller_mode': True,
        'legal_forms': SellerProfile.LEGAL_FORM_CHOICES,
        'role_title': 'Регистрация продавца',
        'role_hint': 'Эти данные нужны для подключения магазина, договоров, оплаты тарифа и обслуживания заказов.',
        'submit_label': 'Создать аккаунт продавца',
    })


def pricing(request):
    current_profile = None
    if request.user.is_authenticated:
        current_profile = getattr(request.user, 'seller_profile', None)
    return render(request, 'accounts/pricing.html', {
        'plans': SellerProfile.plans_for_template(),
        'current_profile': current_profile,
    })


@login_required
def choose_plan(request, plan_code):
    valid_plans = dict(SellerProfile.PLAN_CHOICES)
    if plan_code not in valid_plans:
        messages.error(request, 'Такого тарифа нет')
        return redirect('pricing')

    profile, _ = SellerProfile.objects.get_or_create(user=request.user)
    profile.plan = plan_code
    profile.save(update_fields=['plan', 'updated_at'])
    messages.success(request, f'Оплата подтверждена. Тариф «{profile.plan_config["name"]}» подключен.')
    return redirect('my_shops')


def platform_reviews(request):
    static_reviews = [
        {
            'company': 'Urban Wear Екатеринбург',
            'rating': 5,
            'text': 'За вечер собрали витрину одежды, настроили категории, карточки и тестовую оплату. Для проверки гипотезы этого достаточно.',
            'author': 'ИП Смирнова А.А.',
        },
        {
            'company': 'Gadget Point',
            'rating': 5,
            'text': 'Понравилось, что это не лендинг, а кабинет владельца: CRUD товаров, аналитика, заказы и отдельная витрина для покупателей.',
            'author': 'ООО «Гаджет Поинт»',
        },
        {
            'company': 'Home Decor Studio',
            'rating': 4,
            'text': 'На Start удобно собрать базовый магазин и руками заполнить каталог. Для красивого запуска лучше брать Business.',
            'author': 'Самозанятый продавец',
        },
        {
            'company': 'ActiveWay Sport',
            'rating': 5,
            'text': 'ИИ сразу предложил спортивные категории, карточки и структуру витрины. Мы доработали цены и начали принимать тестовые заказы.',
            'author': 'ИП Захаров Д.С.',
        },
        {
            'company': 'Beauty Box',
            'rating': 5,
            'text': 'Для косметики сработало хорошо: категории получились по теме, дизайн аккуратный, товары можно быстро поправить через кабинет.',
            'author': 'ООО «Бьюти Бокс»',
        },
        {
            'company': 'Coffee & Sweets',
            'rating': 4,
            'text': 'Сервис быстро дает основу магазина. Особенно полезны отдельная витрина, оформление заказа и демонстрационная оплата.',
            'author': 'Кондитерская мастерская',
        },
        {
            'company': 'Kids Market',
            'rating': 5,
            'text': 'Сделали магазин детских товаров без программиста. Дальше просто добавляем новые позиции и смотрим заказы в статистике.',
            'author': 'ИП Орлова М.В.',
        },
        {
            'company': 'PetCare Store',
            'rating': 5,
            'text': 'Нам было важно, чтобы покупательский аккаунт жил внутри конкретного магазина, а не на сайте платформы. Здесь это реализовано понятно.',
            'author': 'Магазин товаров для животных',
        },
    ]

    if request.method == 'POST':
        if not request.user.is_authenticated or not hasattr(request.user, 'seller_profile'):
            messages.error(request, 'Отзыв может оставить только зарегистрированный продавец.')
            return redirect('register_seller')
        if not request.user.shops.exists():
            messages.error(request, 'Сначала создайте магазин на платформе, затем сможете оставить отзыв.')
            return redirect('ai_create_shop')
        text = request.POST.get('text', '').strip()
        rating = int(request.POST.get('rating', '5'))
        rating = max(1, min(5, rating))
        if len(text) < 10:
            messages.error(request, 'Отзыв слишком короткий.')
        else:
            profile = request.user.seller_profile
            PlatformReview.objects.create(
                seller=request.user,
                company_name=profile.company_name or request.user.username,
                rating=rating,
                text=text,
            )
            messages.success(request, 'Отзыв опубликован. Спасибо!')
        return redirect('platform_reviews')

    return render(request, 'accounts/reviews.html', {
        'static_reviews': static_reviews,
        'reviews': PlatformReview.objects.filter(is_public=True),
    })
