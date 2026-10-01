from django.contrib import admin

from .models import Business, Service


class ServiceInline(admin.TabularInline):
    model = Service
    extra = 0


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ["name", "owner", "timezone", "is_active", "created_at"]
    list_filter = ["is_active", "timezone"]
    search_fields = ["name", "owner__email"]
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ServiceInline]


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ["name", "business", "duration_minutes", "price", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name", "business__name"]
