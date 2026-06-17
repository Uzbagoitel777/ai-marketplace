import json
import random
import re
from decimal import Decimal, InvalidOperation

from django.conf import settings
from openai import OpenAI


class HuggingFaceInference:
    def __init__(self):
        self.provider = getattr(settings, 'LLM_PROVIDER', 'lmstudio')
        self.hf_token = getattr(settings, 'HF_TOKEN', '')
        self.lmstudio_base_url = self._normalize_base_url(getattr(settings, 'LMSTUDIO_BASE_URL', 'http://127.0.0.1:1234/v1'))
        self.lmstudio_model = getattr(settings, 'LMSTUDIO_MODEL', 'google/gemma-4-31b-qat')
        self.lmstudio_api_key = getattr(settings, 'LMSTUDIO_API_KEY', 'lm-studio')
        self.timeout = float(getattr(settings, 'LLM_TIMEOUT_SECONDS', 90))
        self.client = None
        self.model = ''

        if self.provider == 'lmstudio':
            self.client = OpenAI(
                base_url=self.lmstudio_base_url,
                api_key=self.lmstudio_api_key,
                timeout=self.timeout,
                max_retries=0,
            )
            self.model = self.lmstudio_model
        elif self.hf_token:
            self.client = OpenAI(
                base_url='https://router.huggingface.co/v1',
                api_key=self.hf_token,
                timeout=self.timeout,
                max_retries=0,
            )
            self.model = 'Qwen/Qwen2.5-7B-Instruct'

    @staticmethod
    def _normalize_base_url(url):
        url = (url or 'http://127.0.0.1:1234/v1').strip().rstrip('/')
        if not url.endswith('/v1'):
            url = f'{url}/v1'
        return url

    def _pick_loaded_lmstudio_model(self):
        if not self.client:
            return self.model
        try:
            models = self.client.models.list()
            for item in models.data:
                model_id = getattr(item, 'id', '')
                if model_id and 'embedding' not in model_id.lower() and 'embed' not in model_id.lower():
                    return model_id
        except Exception:
            return self.model
        return self.model

    def is_local_ai_enabled(self):
        return self.provider == 'lmstudio' and bool(self.client)

    def generate(self, prompt, temperature=0.7, max_tokens=500, system_prompt=None):
        if not self.client:
            return ''

        messages = []
        if system_prompt:
            messages.append({'role': 'system', 'content': system_prompt})
        messages.append({'role': 'user', 'content': prompt})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            result = response.choices[0].message.content or ''
            return re.sub(r'\s+', ' ', result).strip()
        except Exception:
            if self.provider == 'lmstudio':
                fallback_model = self._pick_loaded_lmstudio_model()
                if fallback_model and fallback_model != self.model:
                    try:
                        response = self.client.chat.completions.create(
                            model=fallback_model,
                            messages=messages,
                            temperature=temperature,
                            max_tokens=max_tokens,
                        )
                        self.model = fallback_model
                        result = response.choices[0].message.content or ''
                        return re.sub(r'\s+', ' ', result).strip()
                    except Exception:
                        return ''
            return ''

    @staticmethod
    def _normalize_text(text):
        return (text or '').strip().lower()

    @staticmethod
    def _extract_json(text):
        if not text:
            return None
        text = text.strip()
        text = re.sub(r'^```(?:json)?', '', text, flags=re.IGNORECASE).strip()
        text = re.sub(r'```$', '', text).strip()
        start = text.find('{')
        end = text.rfind('}')
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _safe_decimal(value, default):
        try:
            return Decimal(str(value)).quantize(Decimal('1'))
        except (InvalidOperation, TypeError, ValueError):
            return Decimal(default)

    @staticmethod
    def _clean_string(value, limit=180):
        value = re.sub(r'\s+', ' ', str(value or '')).strip()
        return value[:limit]

    @staticmethod
    def _placeholder_image(name, accent='#4361ee'):
        return ''

    def _profile(self, shop_name, shop_description=''):
        text = self._normalize_text(f'{shop_name} {shop_description}')
        profiles = [
            {
                'keys': ['одеж', 'fashion', 'джинс', 'плать', 'обув', 'стиль', 'streetwear', 'y2k'],
                'categories': ['Женская одежда', 'Мужская одежда', 'Обувь', 'Аксессуары', 'Новинки'],
                'brand': 'Urban Line',
                'products': [
                    ('Футболка oversize Basic', 'Плотный хлопок, свободная посадка и базовые цвета для повседневных образов.', 1290, 24),
                    ('Джинсы прямого кроя Denim Pro', 'Универсальные джинсы с высокой посадкой, подходят под кеды и ботинки.', 3490, 12),
                    ('Худи Premium Cotton', 'Мягкое худи с капюшоном, карманом кенгуру и плотной резинкой на манжетах.', 2990, 18),
                    ('Сумка кросс-боди City', 'Компактная сумка для телефона, документов и повседневных мелочей.', 1690, 20),
                    ('Кроссовки Light Step', 'Легкая повседневная обувь с амортизирующей подошвой.', 4290, 10),
                    ('Топ в рубчик Soft Fit', 'Облегающий топ из эластичной ткани для базовых и летних образов.', 990, 30),
                ],
                'accent': '#7c3aed',
            },
            {
                'keys': ['электрон', 'смартф', 'ноут', 'гаджет', 'техн', 'компьют', 'phone', 'tech'],
                'categories': ['Смартфоны', 'Ноутбуки', 'Аксессуары', 'Умный дом', 'Периферия'],
                'brand': 'TechCore',
                'products': [
                    ('Смартфон Nova X', 'Яркий экран, быстрая зарядка и стабильная работа для повседневных задач.', 24990, 8),
                    ('Беспроводные наушники AirBeat', 'Компактные TWS-наушники с шумоподавлением и зарядным кейсом.', 4990, 25),
                    ('Ноутбук WorkBook 14', 'Легкий ноутбук для учебы, работы с документами и веб-разработки.', 54990, 5),
                    ('Пауэрбанк 20000 мА·ч', 'Внешний аккумулятор с двумя USB-портами и быстрой зарядкой.', 2490, 40),
                    ('Механическая клавиатура RGB', 'Клавиатура с подсветкой, четким ходом клавиш и компактной раскладкой.', 6990, 13),
                    ('Умная колонка Home Mini', 'Голосовое управление музыкой, таймерами и устройствами умного дома.', 5990, 16),
                ],
                'accent': '#2563eb',
            },
            {
                'keys': ['дом', 'интерьер', 'посуда', 'кухн', 'декор', 'мебел', 'уют'],
                'categories': ['Кухня', 'Декор', 'Хранение', 'Текстиль', 'Освещение'],
                'brand': 'Home Space',
                'products': [
                    ('Набор контейнеров Fresh Box', 'Герметичные контейнеры для хранения круп, овощей и готовых блюд.', 1490, 35),
                    ('LED-лампа Cozy Light', 'Теплый свет, экономичное потребление и лаконичный дизайн.', 890, 50),
                    ('Плед Soft Home', 'Мягкий плед для дивана, спальни и уютных вечеров.', 2190, 22),
                    ('Органайзер для кухни', 'Компактная система хранения для специй, приборов и мелочей.', 1290, 27),
                    ('Керамическая кружка Minimal', 'Прочная кружка с матовым покрытием и удобной ручкой.', 690, 60),
                    ('Набор полотенец Comfort', 'Комплект мягких полотенец для ванной и кухни.', 1790, 32),
                ],
                'accent': '#059669',
            },
            {
                'keys': ['спорт', 'фитнес', 'трен', 'туризм', 'вел', 'бег'],
                'categories': ['Фитнес', 'Бег', 'Туризм', 'Спортивная одежда', 'Аксессуары'],
                'brand': 'Active Way',
                'products': [
                    ('Коврик для фитнеса GripMat', 'Нескользящий коврик для тренировок дома, йоги и растяжки.', 1590, 26),
                    ('Бутылка Sport Bottle', 'Легкая бутылка с герметичной крышкой и мерной шкалой.', 790, 45),
                    ('Рюкзак Travel 25L', 'Вместительный рюкзак для прогулок, тренировок и коротких поездок.', 2990, 15),
                    ('Резинки для тренировок Set Pro', 'Комплект эспандеров с разной нагрузкой для силовых упражнений.', 1190, 38),
                    ('Футболка Dry Fit', 'Дышащая футболка для бега, зала и активного отдыха.', 1390, 34),
                    ('Скакалка Speed Rope', 'Легкая скоростная скакалка с регулируемой длиной.', 990, 41),
                ],
                'accent': '#ea580c',
            },
            {
                'keys': ['космет', 'beauty', 'уход', 'макияж', 'парфюм', 'крем', 'волос'],
                'categories': ['Уход за лицом', 'Уход за волосами', 'Макияж', 'Парфюмерия', 'Наборы'],
                'brand': 'Beauty Box',
                'products': [
                    ('Крем увлажняющий Aqua Care', 'Легкий крем для ежедневного ухода, помогает поддерживать кожу мягкой и увлажненной.', 1190, 28),
                    ('Сыворотка Vitamin Glow', 'Сыворотка для сияния кожи с легкой текстурой и удобной пипеткой.', 1690, 18),
                    ('Шампунь Repair Soft', 'Шампунь для мягкого очищения и ухода за волосами после укладки.', 890, 35),
                    ('Палетка Nude Look', 'Базовые оттенки для естественного макияжа на каждый день.', 1490, 16),
                    ('Подарочный набор Spa Day', 'Набор ухода для расслабляющего домашнего spa-ритуала.', 2490, 11),
                    ('Мист для лица Fresh Mist', 'Освежающий мист для быстрого увлажнения в течение дня.', 690, 42),
                ],
                'accent': '#db2777',
            },
            {
                'keys': ['кофе', 'слад', 'еда', 'food', 'чай', 'кондитер', 'торт', 'подарк'],
                'categories': ['Кофе', 'Чай', 'Сладости', 'Подарочные наборы', 'Аксессуары'],
                'brand': 'Coffee & Sweets',
                'products': [
                    ('Кофе зерновой Brazil Medium', 'Сбалансированный кофе средней обжарки с мягким вкусом для дома и офиса.', 990, 30),
                    ('Чай Berry Mix', 'Фруктовый чай с насыщенным ароматом ягод и приятной кислинкой.', 590, 45),
                    ('Набор шоколада Gift Box', 'Подарочный набор шоколада в аккуратной упаковке.', 1290, 22),
                    ('Сироп Vanilla Coffee', 'Сироп для кофе, десертов и домашних напитков.', 490, 40),
                    ('Печенье Butter Cookies', 'Рассыпчатое печенье к кофе и чаю.', 390, 55),
                    ('Термокружка Daily Cup', 'Удобная кружка для напитков с плотной крышкой.', 1190, 18),
                ],
                'accent': '#92400e',
            },
            {
                'keys': ['дет', 'kids', 'игруш', 'ребен', 'малыш', 'школ'],
                'categories': ['Игрушки', 'Одежда', 'Товары для школы', 'Уход', 'Развитие'],
                'brand': 'Kids Market',
                'products': [
                    ('Конструктор Mini Blocks', 'Развивающий конструктор для игры, моторики и воображения.', 1290, 21),
                    ('Рюкзак School Light', 'Легкий школьный рюкзак с удобными отделениями.', 2190, 14),
                    ('Набор для рисования Art Kids', 'Комплект для творчества: карандаши, фломастеры и альбом.', 990, 32),
                    ('Пижама Soft Sleep', 'Мягкая детская пижама для комфортного сна.', 1490, 18),
                    ('Бутылочка Sport Kids', 'Яркая бутылочка для школы, прогулок и тренировок.', 690, 39),
                    ('Развивающая игра Logic Set', 'Настольная игра для внимания, логики и семейного досуга.', 1190, 24),
                ],
                'accent': '#0ea5e9',
            },
            {
                'keys': ['живот', 'pet', 'кот', 'собак', 'корм', 'зоотовар'],
                'categories': ['Корма', 'Игрушки', 'Уход', 'Лежанки', 'Амуниция'],
                'brand': 'PetCare Store',
                'products': [
                    ('Корм Daily Cat', 'Сухой корм для взрослых кошек с понятным составом.', 1290, 26),
                    ('Игрушка Feather Play', 'Игрушка для активных игр кошек и котят.', 390, 50),
                    ('Лежанка Soft Pet', 'Мягкая лежанка для кошек и небольших собак.', 1990, 12),
                    ('Шампунь Pet Clean', 'Средство для бережного ухода за шерстью питомца.', 690, 30),
                    ('Поводок City Walk', 'Прочный поводок для ежедневных прогулок.', 890, 27),
                    ('Миска Steel Bowl', 'Устойчивая миска из нержавеющей стали.', 490, 44),
                ],
                'accent': '#16a34a',
            },
        ]
        for profile in profiles:
            if any(key in text for key in profile['keys']):
                return profile
        return {
            'categories': ['Популярное', 'Новинки', 'Хиты продаж', 'Аксессуары', 'Подарки'],
            'brand': 'AI Market',
            'products': [
                ('Универсальный товар Base', 'Практичный товар для ежедневного использования с хорошим соотношением цены и качества.', 1490, 25),
                ('Премиальный набор Plus', 'Расширенная комплектация для тех, кто хочет получить больше возможностей.', 2990, 12),
                ('Компактный аксессуар Mini', 'Небольшой и удобный аксессуар, который легко взять с собой.', 790, 40),
                ('Подарочный комплект Gift', 'Готовое решение для подарка с аккуратной комплектацией.', 1990, 20),
                ('Новинка сезона Fresh', 'Актуальная позиция с современным дизайном и понятной пользой.', 2490, 18),
                ('Практичный набор Family', 'Набор для дома, семьи или регулярного использования.', 3490, 9),
            ],
            'accent': '#4361ee',
        }

    def _product_count_for_plan(self, plan_code):
        if plan_code == 'business':
            return 50
        if plan_code == 'start':
            return 12
        return 6

    @staticmethod
    def _sanitize_css(css):
        css = str(css or '').strip()
        css = re.sub(r'<\/?style[^>]*>', '', css, flags=re.IGNORECASE)
        css = re.sub(r'@import[^;]+;', '', css, flags=re.IGNORECASE)
        css = re.sub(r'url\s*\([^)]*\)', '', css, flags=re.IGNORECASE)
        css = re.sub(r'expression\s*\([^)]*\)', '', css, flags=re.IGNORECASE)
        return css[:9000]

    def _theme_css(self, accent, template_key, shop_name='', shop_description=''):
        text = self._normalize_text(f'{shop_name} {shop_description}')
        category_css = ''
        if any(k in text for k in ['одеж', 'fashion', 'стиль', 'y2k', 'обув']):
            category_css = """
.ai-page { background: #fff7ed; }
.ai-hero { background: linear-gradient(135deg, #111827 0%, var(--primary) 55%, #f97316 100%); }
.ai-products { grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); }
.ai-product-img { aspect-ratio: .86; }
.ai-category { text-transform: uppercase; letter-spacing: .08em; }
"""
        elif any(k in text for k in ['электрон', 'смартф', 'ноут', 'гаджет', 'техн', 'компьют']):
            category_css = """
.ai-page { background: radial-gradient(circle at top left, rgba(37,99,235,.18), transparent 28%), #f8fafc; }
.ai-hero { background: linear-gradient(135deg, #020617 0%, #172554 52%, var(--primary) 100%); }
.ai-product-card { background: rgba(255,255,255,.78); backdrop-filter: blur(18px); }
.ai-category { border-left: 5px solid var(--primary); }
"""
        elif any(k in text for k in ['кофе', 'слад', 'еда', 'чай', 'кондитер']):
            category_css = """
.ai-page { background: #f7efe5; }
.ai-hero { background: linear-gradient(135deg, #3f2415 0%, #7c2d12 58%, #f59e0b 100%); }
.ai-product-card, .ai-info-card, .ai-category { border-radius: 34px; }
.ai-price { color: #7c2d12; }
"""
        elif any(k in text for k in ['космет', 'beauty', 'уход', 'макияж']):
            category_css = """
.ai-page { background: linear-gradient(180deg, #fff1f2, #ffffff); }
.ai-hero { background: linear-gradient(135deg, #be185d 0%, var(--primary) 48%, #f9a8d4 100%); }
.ai-product-card { border-radius: 36px 36px 14px 14px; }
.ai-hero h1 { font-family: Georgia, serif; font-weight: 700; }
"""
        elif any(k in text for k in ['дом', 'интерьер', 'посуда', 'кухн', 'уют']):
            category_css = """
.ai-page { background: #f5f3ef; }
.ai-hero { background: linear-gradient(135deg, #064e3b 0%, var(--primary) 60%, #d9f99d 100%); }
.ai-shell { max-width: 1180px; }
.ai-product-card { border-radius: 10px; }
.ai-info-card { background: #fffaf0; }
"""
        elif any(k in text for k in ['спорт', 'фитнес', 'трен', 'туризм']):
            category_css = """
.ai-page { background: #f1f5f9; }
.ai-hero { background: linear-gradient(135deg, #0f172a 0%, #ea580c 52%, #fde047 100%); transform: skewY(-1deg); }
.ai-hero > * { transform: skewY(1deg); }
.ai-product-card:hover { transform: translateY(-8px) scale(1.015); }
.ai-buy { text-transform: uppercase; letter-spacing: .04em; }
"""
        else:
            category_css = """
.ai-hero { background: linear-gradient(135deg, var(--primary) 0%, #111827 100%); }
"""

        template_css = {
            'modern': """
.ai-header { border-bottom: 1px solid rgba(15,23,42,.08); }
.ai-hero { border-radius: 38px; }
.ai-product-card { transition: transform .18s ease, box-shadow .18s ease; }
""",
            'minimal': """
.ai-page { background: #fff; }
.ai-hero, .ai-product-card, .ai-category, .ai-info-card { border-radius: 0; box-shadow: none; }
.ai-hero { min-height: 380px; }
.ai-product-card { border-width: 0 0 1px 0; }
""",
            'premium': """
.ai-page { background: radial-gradient(circle at top, rgba(212,175,55,.22), transparent 32%), #0b1020; }
.ai-header { background: rgba(11,16,32,.78); }
.ai-logo a, .ai-nav a, .ai-nav span { color: white; }
.ai-shell { color: #f8fafc; }
.ai-section-note, .ai-info-card p, .ai-info-card li { color: rgba(248,250,252,.72); }
.ai-category, .ai-product-card, .ai-info-card { background: rgba(255,255,255,.08); border-color: rgba(255,255,255,.16); color: white; backdrop-filter: blur(18px); }
.ai-product-body p, .ai-delivery { color: rgba(248,250,252,.7); }
.ai-hero { background: linear-gradient(135deg, #020617 0%, var(--primary) 52%, #d4af37 100%); }
""",
        }.get(template_key, '')
        return self._sanitize_css(f':root{{--primary:{accent};}}\n{category_css}\n{template_css}')

    def _fallback_bundle(self, shop_name, shop_description='', plan_code='free', template_key='modern', city='Екатеринбург', address=''):
        profile = self._profile(shop_name, shop_description)
        product_count = self._product_count_for_plan(plan_code)
        categories = profile['categories'][:5]
        description = (
            f'{shop_name} — интернет-магазин, который создан на платформе ИИ-конструктора. '
            f'Витрина собрана под тематику: {shop_description or ", ".join(categories[:3]).lower()}. '
            'Продавец может редактировать товары, категории, доставку, оплату и дизайн через личный кабинет.'
        )

        products = []
        source_products = profile['products'][:]
        random.seed(f'{shop_name}:{shop_description}:{template_key}:{plan_code}')
        random.shuffle(source_products)
        for index in range(1, product_count + 1):
            name, desc, price, stock = source_products[(index - 1) % len(source_products)]
            if product_count > len(source_products):
                name = f'{name} #{index}'
                price = int(Decimal(price) + (index % 7) * Decimal('120'))
                stock = max(3, int(stock) + (index % 9))
            products.append({
                'name': name,
                'description': desc,
                'category': categories[(index - 1) % len(categories)],
                'brand': profile['brand'],
                'price': str(Decimal(price)),
                'stock': stock,
                'image_url': '',
            })

        news = [{
            'title': 'Магазин создан',
            'content': 'Витрина создана. Владелец может управлять каталогом, заказами, аналитикой и внешним видом магазина.',
        }]
        if plan_code != 'start':
            news.append({
                'title': 'Стартовое наполнение готово',
                'content': 'Категории и товары подобраны под тематику магазина. Каталог можно расширять через CRUD-кабинет.',
            })

        return {
            'name': shop_name,
            'description': description,
            'categories': categories,
            'products': products,
            'news': news,
            'theme_color': profile['accent'],
            'custom_css': self._theme_css(profile['accent'], template_key, shop_name, shop_description),
            'template_key': template_key,
            'plan_code': plan_code,
            'city': city or 'Екатеринбург',
            'address': address,
            'delivery': {
                'enabled': True,
                'price': '299',
                'description': 'Доставка рассчитывается примерно по городу магазина, адресу клиента и выбранной службе доставки.',
            },
            'payment': {
                'enabled': True,
                'methods': 'Банковская карта, оплата при получении, тестовая онлайн-оплата',
            },
        }

    def _build_store_prompt(self, shop_name, shop_description, plan_code, product_count, template_key):
        return f'''
Ты генератор интернет-магазинов для платформы AI Партнёры. Создай ПОЛНУЮ структуру сайта на русском языке.
Название магазина: {shop_name}
Идея/тематика: {shop_description or 'не указана'}
Тариф: {plan_code}
Базовый каркас: {template_key}
Количество карточек товаров: {product_count}

Тебе НЕ нужно писать HTML целиком. Django хранит безопасный каркас страницы, а ты генерируешь: контент, категории, товары, секции, цветовую схему и CSS для классов каркаса.

Верни только валидный JSON без markdown, без ``` и без пояснений.
Схема строго такая:
{{
  "store_name": "...",
  "description": "2-3 предложения о магазине",
  "theme_color": "#2563eb",
  "categories": ["категория 1", "категория 2", "категория 3", "категория 4", "категория 5"],
  "brand": "название общего бренда магазина",
  "products": [
    {{"name": "...", "category": "одна из categories", "brand": "...", "description": "1-2 предложения", "price": 1990, "stock": 15}}
  ],
  "news": [
    {{"title": "короткий заголовок", "content": "короткая новость магазина"}}
  ],
  "sections": [
    {{"title": "Преимущество", "text": "краткий текст"}},
    {{"title": "Доставка", "text": "краткий текст"}},
    {{"title": "Почему выбирают нас", "text": "краткий текст"}}
  ],
  "custom_css": "CSS только для классов .ai-page, .ai-header, .ai-hero, .ai-category, .ai-product-card, .ai-info-card, .ai-buy, .ai-product-visual. Без HTML, JS, @import и external url."
}}

Правила:
- products должен содержать ровно {product_count} товаров.
- Не генерируй фото, image_url, ссылки на Unsplash, placehold, внешние url и base64.
- Названия категорий и товаров должны строго соответствовать тематике магазина.
- custom_css обязан заметно менять внешний вид: фон, hero, карточки, сетку, радиусы, тени, цвета.
- Используй только безопасный CSS без @import, url(), javascript, expression, комментариев и HTML.
- Если не уверен в цене, ставь реалистичную цену в рублях числом.
'''.strip()

    def _normalize_ai_bundle(self, raw, shop_name, shop_description, plan_code, template_key, city, address, requested_product_count=None):
        fallback = self._fallback_bundle(shop_name, shop_description, plan_code, template_key, city, address)
        data = self._extract_json(raw)
        if not isinstance(data, dict):
            return fallback

        product_count = max(1, min(50, int(requested_product_count or self._product_count_for_plan(plan_code))))
        accent = self._clean_string(data.get('theme_color'), 20)
        if not re.fullmatch(r'#[0-9a-fA-F]{6}', accent or ''):
            accent = fallback['theme_color']

        categories = data.get('categories') if isinstance(data.get('categories'), list) else []
        categories = [self._clean_string(item, 80) for item in categories if self._clean_string(item, 80)]
        if len(categories) < 3:
            categories = fallback['categories']
        categories = categories[:8]

        raw_products = data.get('products') if isinstance(data.get('products'), list) else []
        products = []
        for index, item in enumerate(raw_products[:product_count], start=1):
            if not isinstance(item, dict):
                continue
            name = self._clean_string(item.get('name'), 160) or f'Товар #{index}'
            category = self._clean_string(item.get('category'), 80)
            if category not in categories:
                category = categories[(index - 1) % len(categories)]
            price = self._safe_decimal(item.get('price'), 1490)
            stock = item.get('stock', 10)
            try:
                stock = max(1, min(999, int(stock)))
            except (TypeError, ValueError):
                stock = 10
            fallback_description = fallback['products'][0]['description'] if fallback['products'] else 'Описание товара создано ИИ.'
            fallback_brand = fallback['products'][0]['brand'] if fallback['products'] else 'AI Brand'
            description = self._clean_string(item.get('description'), 800) or fallback_description
            brand = self._clean_string(item.get('brand'), 100) or self._clean_string(data.get('brand'), 100) or fallback_brand
            products.append({
                'name': name,
                'description': description,
                'category': category,
                'brand': brand,
                'price': str(price),
                'stock': stock,
                'image_url': '',
            })

        if product_count and len(products) < product_count:
            extra = fallback['products']
            while len(products) < product_count and extra:
                source = extra[len(products) % len(extra)].copy()
                if product_count > len(extra):
                    source['name'] = f'{source["name"]} #{len(products) + 1}'
                source['image_url'] = ''
                products.append(source)

        news = []
        for item in data.get('news', [])[:3] if isinstance(data.get('news'), list) else []:
            if isinstance(item, dict):
                title = self._clean_string(item.get('title'), 120)
                content = self._clean_string(item.get('content'), 700)
                if title and content:
                    news.append({'title': title, 'content': content})
        for item in data.get('sections', [])[:3] if isinstance(data.get('sections'), list) else []:
            if isinstance(item, dict):
                title = self._clean_string(item.get('title'), 120)
                content = self._clean_string(item.get('text'), 700)
                if title and content:
                    news.append({'title': title, 'content': content})
        if not news:
            news = fallback['news']
        news = news[:5]

        return {
            'name': self._clean_string(data.get('store_name'), 100) or shop_name,
            'description': self._clean_string(data.get('description'), 1000) or fallback['description'],
            'categories': categories,
            'products': products,
            'news': news,
            'theme_color': accent,
            'custom_css': self._sanitize_css(data.get('custom_css')) or self._theme_css(accent, template_key, shop_name, shop_description),
            'template_key': template_key,
            'plan_code': plan_code,
            'city': city or 'Екатеринбург',
            'address': address,
            'delivery': fallback['delivery'],
            'payment': fallback['payment'],
        }

    def generate_categories(self, shop_name, shop_description=''):
        profile = self._profile(shop_name, shop_description)
        return profile['categories'][:5]

    def generate_shop_description(self, shop_name, products_info=''):
        prompt = f"Напиши продающее описание интернет-магазина '{shop_name}' на русском языке. Тематика: {products_info}. 2-3 предложения, без списков."
        result = self.generate(prompt, temperature=0.7, max_tokens=220)
        if result:
            return result.strip()
        return self._fallback_bundle(shop_name, products_info)['description']

    def generate_product_description(self, product_name, category_name=None, shop_name=None):
        prompt = f"Напиши привлекательное описание товара '{product_name}'"
        if category_name:
            prompt += f" в категории '{category_name}'"
        if shop_name:
            prompt += f" для магазина '{shop_name}'"
        prompt += '. Русский язык, 2-3 предложения, без списков и markdown.'
        result = self.generate(prompt, temperature=0.8, max_tokens=280)
        if result:
            return result.strip()
        category_text = f' из категории «{category_name}»' if category_name else ''
        return f'{product_name}{category_text} — удачный выбор для ежедневного использования. Товар сочетает понятную пользу, аккуратное исполнение и честную цену.'

    def generate_storefront_bundle(self, shop_name, shop_description='', plan_code='free', template_key='modern', city='Екатеринбург', address='', use_ai=True, favorite_color='', design_notes='', revision_request='', requested_product_count=None):
        if favorite_color or design_notes or revision_request:
            shop_description = f'{shop_description} Предпочтительный цвет: {favorite_color or "не указан"}. Пожелания к дизайну: {design_notes or "нет"}. Правки: {revision_request or "нет"}.'
        if not use_ai:
            bundle = self._fallback_bundle(shop_name, shop_description, plan_code, template_key, city, address)
            if re.fullmatch(r'#[0-9a-fA-F]{6}', favorite_color or ''):
                bundle['theme_color'] = favorite_color
                bundle['custom_css'] = self._theme_css(favorite_color, template_key, shop_name, shop_description)
            return bundle

        product_count = max(1, min(50, int(requested_product_count or self._product_count_for_plan(plan_code))))
        prompt = self._build_store_prompt(shop_name, shop_description, plan_code, product_count, template_key)
        system_prompt = 'Ты модуль генерации интернет-магазинов. Всегда возвращай только валидный JSON по заданной схеме.'
        raw = self.generate(prompt, temperature=0.25, max_tokens=3200, system_prompt=system_prompt)
        bundle = self._normalize_ai_bundle(raw, shop_name, shop_description, plan_code, template_key, city, address, product_count)
        if re.fullmatch(r'#[0-9a-fA-F]{6}', favorite_color or ''):
            bundle['theme_color'] = favorite_color
            bundle['custom_css'] = self._theme_css(favorite_color, template_key, shop_name, shop_description) + '\n' + (bundle.get('custom_css') or '')
        return bundle

    def chat_with_customer(self, question, products_info):
        if len(products_info) > 5000:
            products_info = products_info[:5000]
        system_prompt = '''Ты ИИ-консультант интернет-магазина. Отвечай на русском языке, кратко и полезно. Используй только каталог, который тебе передали. Не придумывай товары, которых нет в каталоге. Если покупатель просит выбрать товар, предложи 1-3 конкретных варианта из каталога. Если просит доставку или оплату, объясни доступный сценарий. Если просит добавить товар, скажи точное название товара, которое нужно добавить.'''
        prompt = f'Каталог магазина:\n{products_info}\n\nВопрос покупателя: {question}'
        result = self.generate(prompt, temperature=0.55, max_tokens=450, system_prompt=system_prompt)
        if result:
            return result.strip()

        q = self._normalize_text(question)
        lines = [line.strip('- ').strip() for line in products_info.split('\n') if line.strip().startswith('-')]
        first = lines[0] if lines else ''
        cheapest = None
        for line in lines:
            match = re.search(r':\s*([0-9]+(?:[.,][0-9]+)?)\s*руб', line)
            if match:
                price = Decimal(match.group(1).replace(',', '.'))
                if cheapest is None or price < cheapest[0]:
                    cheapest = (price, line)
        target = cheapest[1] if any(word in q for word in ['дешев', 'бюджет', 'недорог']) and cheapest else first
        if any(word in q for word in ['достав', 'привез', 'получ', 'самовывоз']):
            return 'Можно выбрать самовывоз или доставку. При оформлении заказа система попросит город, адрес и службу доставки, затем рассчитает примерную стоимость.'
        if any(word in q for word in ['оплат', 'карт', 'налич', 'сбп']):
            return 'Оплата работает в демо-режиме: можно выбрать карту, СБП или оплату при получении. Форма карты нужна только для реалистичного показа сценария.'
        if target:
            return f'Под ваш запрос подходит: {target}. Могу помочь добавить товар в корзину или избранное.'.replace('руб.', '₽')
        return 'Каталог пока пустой или запрос слишком общий. Напишите название товара, категорию или бюджет — я подберу вариант.'

    def generate_news(self, shop_name, news_topic=''):
        prompt = f"Напиши короткую новость для магазина '{shop_name}' на тему '{news_topic or 'обновление каталога'}'. Русский язык, 3 предложения."
        result = self.generate(prompt, temperature=0.8, max_tokens=250)
        if result:
            return result.strip()
        return f'В магазине «{shop_name}» появилось обновление: {news_topic or "обновление каталога"}. Мы обновляем витрину и делаем выбор товаров удобнее.'

    @staticmethod
    def dump_bundle(bundle):
        return json.dumps(bundle, ensure_ascii=False, indent=2)
