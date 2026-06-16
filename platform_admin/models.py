from django.db import models
from django.contrib.auth.models import User

class PlatformAdmin(models.Model):
    """Главный администратор платформы"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='platform_admin')
    is_super_admin = models.BooleanField(default=True, verbose_name='Супер администратор')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Админ: {self.user.username}"
    
    class Meta:
        verbose_name = 'Администратор платформы'
        verbose_name_plural = 'Администраторы платформы'