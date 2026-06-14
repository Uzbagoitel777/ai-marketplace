from openai import OpenAI
from django.conf import settings

class HuggingFaceInference:
    def __init__(self):
        self.api_token = getattr(settings, 'HF_TOKEN', None)
        self.model = "Qwen/Qwen2.5-7B-Instruct"  # Рабочая модель
        
        if self.api_token:
            self.client = OpenAI(
                base_url="https://router.huggingface.co/v1",
                api_key=self.api_token
            )
    
    def generate(self, prompt, temperature=0.7, max_tokens=500):
        if not self.api_token:
            return "Ошибка: не настроен HF_TOKEN. Добавьте HF_TOKEN в файл .env"
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Ошибка при обращении к Hugging Face API: {str(e)}"
    
    def generate_product_description(self, product_name, category_name=None, shop_name=None):
        prompt = f"Напиши привлекательное описание для товара '{product_name}'"
        if category_name:
            prompt += f" в категории '{category_name}'"
        if shop_name:
            prompt += f" для магазина '{shop_name}'"
        prompt += " Описание должно быть информативным, содержать преимущества товара и быть длиной 2-3 предложения. Ответ пиши на русском языке."
        
        return self.generate(prompt, temperature=0.8, max_tokens=300)
    
    def generate_categories(self, shop_name, shop_description=""):
        prompt = f"""Магазин называется "{shop_name}"
Описание магазина: {shop_description if shop_description else "не указано"}

Предложи 5 категорий товаров, которые подходят для этого магазина.
Категории должны быть на русском языке, каждая категория на новой строке, без нумерации.
Напиши только категории, без дополнительного текста.

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
            if line and len(line) < 50 and not line.startswith('Пример'):
                categories.append(line)
        
        if not categories:
            categories = ["Товары", "Новинки", "Акции", "Рекомендуемые", "Популярные"]
        
        return categories[:5]
    
    def generate_shop_description(self, shop_name, products_info=""):
        prompt = f"Напиши привлекательное описание для интернет-магазина '{shop_name}'"
        if products_info:
            prompt += f", который продает {products_info}"
        prompt += " Описание должно быть кратким, продающим и показывать преимущества магазина (2-3 предложения). Ответ пиши на русском языке."
        
        return self.generate(prompt, temperature=0.8, max_tokens=200)
    
    def chat_with_customer(self, question, products_info):
        if len(products_info) > 3000:
            products_info = products_info[:3000]
        
        prompt = f"""Ты - ИИ-помощник в интернет-магазине.
Доступные товары:
{products_info}

Покупатель спрашивает: "{question}"

Ответь вежливо и полезно. Если товара нет, предложи альтернативу или скажи, когда появится.
Будь кратким и дружелюбным. Ответ пиши на русском языке."""
        
        return self.generate(prompt, temperature=0.7, max_tokens=300)
    
    def generate_news(self, shop_name, news_topic=""):
        prompt = f"Напиши короткую новость для интернет-магазина '{shop_name}'"
        if news_topic:
            prompt += f" на тему: {news_topic}"
        prompt += " Новость должна быть интересной для покупателей (3-4 предложения). Ответ пиши на русском языке."
        
        return self.generate(prompt, temperature=0.8, max_tokens=250)