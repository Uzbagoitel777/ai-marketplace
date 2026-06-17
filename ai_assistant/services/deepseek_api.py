from openai import OpenAI
from django.conf import settings

class DeepSeekAPI:
    def __init__(self):
        self.api_key = getattr(settings, 'DEEPSEEK_API_KEY', None)
        
        if not self.api_key:
            print("ВНИМАНИЕ: DEEPSEEK_API_KEY не настроен")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.deepseek.com"
        )
    
    def generate(self, prompt, temperature=0.7, max_tokens=500):
        """Отправляет запрос к DeepSeek API и возвращает ответ"""
        if not self.api_key:
            return "Ошибка: не настроен API ключ DeepSeek. Добавьте DEEPSEEK_API_KEY в файл .env"
        
        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Ошибка при обращении к DeepSeek API: {str(e)}"
    
    def generate_product_description(self, product_name, category_name=None, shop_name=None):
        """Генерация описания товара"""
        prompt = f"Напиши привлекательное описание для товара '{product_name}'"
        if category_name:
            prompt += f" в категории '{category_name}'"
        if shop_name:
            prompt += f" для магазина '{shop_name}'"
        prompt += "\nОписание должно быть информативным, содержать преимущества товара и быть длиной 2-3 предложения. Ответ пиши на русском языке."
        
        return self.generate(prompt, temperature=0.8, max_tokens=300)
    
    def generate_categories(self, shop_name, shop_description=""):
        """Генерация категорий для магазина"""
        prompt = f"""Магазин называется "{shop_name}"
Описание магазина: {shop_description if shop_description else "не указано"}

Предложи 5-7 категорий товаров, которые подходят для этого магазина.
Категории должны быть в формате списка, каждая категория на новой строке.
Категории должны быть на русском языке, без нумерации, просто слова.

Пример:
Электроника
Одежда
Обувь
Аксессуары
Дом и сад"""
        
        response = self.generate(prompt, temperature=0.7, max_tokens=200)
        
        categories = []
        for line in response.split('\n'):
            line = line.strip()
            if line.startswith('-') or line.startswith('•') or line.startswith('*'):
                line = line[1:].strip()
            if line and line[0].isdigit() and '.' in line[:3]:
                line = line.split('.', 1)[1].strip()
            if line and not line.startswith('Пример'):
                categories.append(line)
        
        return categories[:7]
    
    def generate_shop_description(self, shop_name, products_info=""):
        """Генерация описания магазина"""
        prompt = f"Напиши привлекательное описание для интернет-магазина '{shop_name}'"
        if products_info:
            prompt += f", который продает {products_info}"
        prompt += "\nОписание должно быть кратким, продающим и показывать преимущества магазина (2-3 предложения). Ответ пиши на русском языке."
        
        return self.generate(prompt, temperature=0.8, max_tokens=200)
    
    def chat_with_customer(self, question, products_info):
        """Чат для покупателя на витрине"""
        if len(products_info) > 3000:
            products_info = products_info[:3000] + "..."
        
        prompt = f"""Ты - ИИ-помощник в интернет-магазине.
Доступные товары:
{products_info}

Покупатель спрашивает: "{question}"

Ответь вежливо и полезно. Если товара нет, предложи альтернативу или скажи, когда появится.
Будь кратким и дружелюбным. Ответ пиши на русском языке."""
        
        return self.generate(prompt, temperature=0.7, max_tokens=300)
    
    def generate_news(self, shop_name, news_topic=""):
        """Генерация новости для магазина"""
        prompt = f"Напиши короткую новость для интернет-магазина '{shop_name}'"
        if news_topic:
            prompt += f" на тему: {news_topic}"
        prompt += "\nНовость должна быть интересной для покупателей (3-4 предложения). Ответ пиши на русском языке."
        
        return self.generate(prompt, temperature=0.8, max_tokens=250)
