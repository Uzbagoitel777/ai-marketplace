from django.contrib import admin
from django.urls import path, include
from shops.views import home

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('shops/', include('shops.urls')),
    path('ai/', include('ai_assistant.urls')),
    path('platform-admin/', include('platform_admin.urls')),
]