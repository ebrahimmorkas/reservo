import django_filters

from .models import Service


class ServiceFilter(django_filters.FilterSet):
    business = django_filters.CharFilter(field_name="business__slug")
    min_price = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr="lte")
    max_duration = django_filters.NumberFilter(field_name="duration_minutes", lookup_expr="lte")

    class Meta:
        model = Service
        fields = ["business", "is_active"]
