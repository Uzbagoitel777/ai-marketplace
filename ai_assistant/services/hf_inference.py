import re
from openai import OpenAI
from django.conf import settings

class HuggingFaceInference:
    def __init__(self):
        self.api_token = getattr(settings, 'HF_TOKEN', None)
        self.model = "Qwen/Qwen2.5-7B-Instruct"
        
        if self.api_token:
            self.client = OpenAI(
                base_url="https://router.huggingface.co/v1",
                api_key=self.api_token
            )
    
    def generate(self, prompt, temperature=0.7, max_tokens=500):
        if not self.api_token:
            return "Ошибка: не настроен HF_TOKEN"
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            result = response.choices[0].message.content
            
            result = re.sub(r'[\u4e00-\u9fff\u3400-\u4dbf\u3000-\u303f]+', '', result)
            result = re.sub(r'\s+', ' ', result).strip()
            
            return result
        except Exception as e:
            return f"Ошибка: {str(e)}"
    
    def generate_product_description(self, product_name, category_name=None, shop_name=None):
        prompt = f"Напиши привлекательное описание для товара '{product_name}' на русском языке. 2-3 предложения."
        
        if category_name:
            prompt = f"Напиши привлекательное описание для товара '{product_name}' в категории '{category_name}' на русском языке. 2-3 предложения."
        
        return self.generate(prompt, temperature=0.8, max_tokens=300)
    
    def generate_categories(self, shop_name, shop_description=""):
        prompt = f"""Магазин "{shop_name}". Предложи 5 категорий товаров на русском языке.
Категории на новой строке, без нумерации.
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
            if line and len(line) < 50:
                categories.append(line)
        
        if not categories:
            categories = ["Товары", "Новинки", "Акции", "Рекомендуемые", "Популярные"]
        
        return categories[:5]
    
    def generate_shop_description(self, shop_name, products_info=""):
        prompt = f"Напиши привлекательное описание для интернет-магазина '{shop_name}' на русском языке. 2-3 предложения."
        
        if products_info:
            prompt = f"Напиши привлекательное описание для интернет-магазина '{shop_name}', который продает {products_info} на русском языке. 2-3 предложения."
        
        result = self.generate(prompt, temperature=0.7, max_tokens=200)
        result = re.sub(r'Добро пожаловать.*?\n', '', result)
        result = result.strip()
        
        return result
    
    def chat_with_customer(self, question, products_info):
        if len(products_info) > 3000:
            products_info = products_info[:3000]
        
        prompt = f"""Ты - помощник в магазине.
Товары:
{products_info}

Вопрос: "{question}"

Ответь вежливо и полезно на русском языке."""
        
        return self.generate(prompt, temperature=0.7, max_tokens=300)