from django.contrib import admin

from .models import CustomerProfile, PlatformReview, SellerProfile


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'created_at')
    search_fields = ('user__username', 'phone')


@admin.register(SellerProfile)
class SellerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'company_name', 'legal_form', 'inn', 'plan', 'is_approved', 'created_at')
    list_filter = ('plan', 'legal_form', 'is_approved')
    search_fields = ('user__username', 'company_name', 'inn', 'phone')


@admin.register(PlatformReview)
class PlatformReviewAdmin(admin.ModelAdmin):
    list_display = ('seller', 'company_name', 'rating', 'is_public', 'created_at')
    list_filter = ('rating', 'is_public')
    search_fields = ('seller__username', 'company_name', 'text')
