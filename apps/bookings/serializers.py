from rest_framework import serializers

from apps.catalog.models import Service

from .models import Booking


class BookingSerializer(serializers.ModelSerializer):
    service = serializers.PrimaryKeyRelatedField(
        queryset=Service.objects.select_related("business")
    )
    service_name = serializers.CharField(source="service.name", read_only=True)
    business = serializers.SlugRelatedField(slug_field="slug", read_only=True)
    customer = serializers.EmailField(source="customer.email", read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id",
            "service",
            "service_name",
            "business",
            "customer",
            "starts_at",
            "ends_at",
            "status",
            "price",
            "notes",
            "cancelled_at",
            "cancellation_reason",
            "created_at",
        ]
        read_only_fields = [
            "ends_at",
            "status",
            "price",
            "cancelled_at",
            "cancellation_reason",
            "created_at",
        ]


class RescheduleSerializer(serializers.Serializer):
    starts_at = serializers.DateTimeField()


class CancelSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=255, required=False, allow_blank=True)
