import django_filters

from .models import Booking


class BookingFilter(django_filters.FilterSet):
    business = django_filters.CharFilter(field_name="business__slug")
    starts_after = django_filters.IsoDateTimeFilter(field_name="starts_at", lookup_expr="gte")
    starts_before = django_filters.IsoDateTimeFilter(field_name="starts_at", lookup_expr="lt")
    role = django_filters.ChoiceFilter(
        choices=[("customer", "As customer"), ("provider", "As provider")],
        method="filter_role",
    )

    class Meta:
        model = Booking
        fields = ["status", "service"]

    def filter_role(self, queryset, name, value):
        user = self.request.user
        if value == "customer":
            return queryset.filter(customer=user)
        return queryset.filter(business__owner=user)
