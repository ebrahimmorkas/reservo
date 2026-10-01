from django.contrib import admin

from .models import TimeOff, WorkingHours


@admin.register(WorkingHours)
class WorkingHoursAdmin(admin.ModelAdmin):
    list_display = ["business", "weekday", "start_time", "end_time"]
    list_filter = ["weekday"]
    search_fields = ["business__name"]


@admin.register(TimeOff)
class TimeOffAdmin(admin.ModelAdmin):
    list_display = ["business", "starts_at", "ends_at", "reason"]
    search_fields = ["business__name", "reason"]
    date_hierarchy = "starts_at"
