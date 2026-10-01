from django.contrib import admin

from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ["id", "service", "business", "customer", "starts_at", "status", "price"]
    list_filter = ["status", "business"]
    search_fields = ["customer__email", "service__name", "business__name"]
    date_hierarchy = "starts_at"
    list_select_related = ["service", "business", "customer"]
    readonly_fields = ["created_at", "updated_at", "cancelled_at", "reminder_sent_at"]
