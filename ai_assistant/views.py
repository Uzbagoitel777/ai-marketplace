from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils.text import slugify
import time
from .services.hf_inference import HuggingFaceInference
from shops.models import Shop, Category

def init_ai():
    return HuggingFaceInference()

@login_required
def ai_create_shop(request):
    if request.method == 'POST':
        shop_name = request.POST.get('shop_name')
        shop_description = request.POST.get('shop_description', '')
        design_description = request.POST.get('design_description', '')
        
        if not shop_name:
            messages.error(request, 'Введите название магазина')
            return redirect('ai_create_shop')
        
        try:
            ai = init_ai()
            
            generated_description = ai.generate_shop_description(shop_name, shop_description)
            categories = ai.generate_categories(shop_name, shop_description)
            custom_css = ai.generate_custom_css(shop_name, design_description)
            
            request.session['ai_shop_data'] = {
                'name': shop_name,
                'description': generated_description,
                'categories': categories,
                'custom_css': custom_css,
                'design_description': design_description,
            }
            
            return render(request, 'ai_assistant/confirm_shop.html', {
                'shop_name': shop_name,
                'generated_description': generated_description,
                'categories': categories,
                'custom_css': custom_css,
                'design_description': design_description,
            })
        except Exception as e:
            messages.error(request, f'Ошибка при генерации: {str(e)}')
            return redirect('ai_create_shop')
    
    return render(request, 'ai_assistant/create_shop_ai.html')

@login_required
def confirm_create_shop(request):
    if request.method == 'POST':
        shop_data = request.session.get('ai_shop_data')
        if not shop_data:
            messages.error(request, 'Данные не найдены, начните заново')
            return redirect('ai_create_shop')
        
        slug = slugify(shop_data['name'])
        if not slug:
            slug = f"shop-{request.user.id}-{int(time.time())}"
        
        original_slug = slug
        counter = 1
        while Shop.objects.filter(slug=slug).exists():
            slug = f"{original_slug}-{counter}"
            counter += 1
        
        shop = Shop.objects.create(
            owner=request.user,
            name=shop_data['name'],
            slug=slug,
            description=shop_data['description'],
            custom_css=shop_data.get('custom_css', ''),
        )
        
        for category_name in shop_data['categories'][:5]:
            if category_name and len(category_name) <= 100:
                Category.objects.create(
                    shop=shop,
                    name=category_name,
                    order=0
                )
        
        messages.success(request, f'Магазин "{shop.name}" успешно создан с помощью ИИ!')
        
        if 'ai_shop_data' in request.session:
            del request.session['ai_shop_data']
        
        return redirect('shop_manage', shop_slug=shop.slug)
    
    return redirect('ai_create_shop')

@login_required
def generate_product_description_ajax(request):
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        product_name = data.get('product_name')
        category_name = data.get('category_name', '')
        
        ai = init_ai()
        description = ai.generate_product_description(product_name, category_name)
        
        return JsonResponse({'description': description})
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

def ai_chat(request, shop_slug):
    from shops.models import Shop
    
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        question = data.get('question')
        
        try:
            shop = Shop.objects.get(slug=shop_slug)
            
            products = shop.products.all()[:20]
            if products.exists():
                products_info = "\n".join([f"- {p.name}: {p.price} руб. (в наличии: {p.stock} шт.)" for p in products])
            else:
                products_info = "В магазине пока нет товаров"
            
            ai = init_ai()
            answer = ai.chat_with_customer(question, products_info)
            
            return JsonResponse({'answer': answer})
        except Shop.DoesNotExist:
            return JsonResponse({'answer': 'Магазин не найден'}, status=404)
        except Exception as e:
            return JsonResponse({'answer': f'Извините, произошла ошибка: {str(e)}'})
    
    return JsonResponse({'error': 'Invalid request'}, status=400)