

Платформа для создания интернет-магазинов с ИИ-помощником.

## Функциональность

- Создание интернет-магазинов через ИИ-помощника
- Управление товарами, категориями, брендами и новостями
- Публичная витрина для покупателей
- Админ-панель Django
- Несколько магазинов у одного пользователя

## Технологии

- Python 3.11
- Django 5.x
- SQLite
- HTML/CSS
- YandexGPT API (планируется)

## Установка

```bash
# Клонируем репозиторий
git clone https://github.com/ZeroUzer/ai.git

# Переходим в папку
cd ai-shop-platform

# Создаем виртуальное окружение
python -m venv venv

# Активируем (Windows)
venv\Scripts\activate

# Устанавливаем зависимости
pip install -r requirements.txt

# Применяем миграции
python manage.py migrate

# Создаем суперпользователя
python manage.py createsuperuser

# Запускаем сервер
python manage.py runserver