from rest_framework import serializers

from .models import Business, Service


class ServiceSerializer(serializers.ModelSerializer):
    business = serializers.SlugRelatedField(slug_field="slug", queryset=Business.objects.all())

    class Meta:
        model = Service
        fields = [
            "id",
            "business",
            "name",
            "description",
            "duration_minutes",
            "buffer_minutes",
            "price",
            "is_active",
        ]

    def validate_business(self, business: Business) -> Business:
        request = self.context["request"]
        if business.owner_id != request.user.id:
            raise serializers.ValidationError("You can only add services to your own business.")
        return business

    def validate(self, attrs):
        # Moving a service to another business is not supported.
        if self.instance and "business" in attrs and attrs["business"] != self.instance.business:
            raise serializers.ValidationError({"business": "Cannot be changed."})
        return attrs


class BusinessSerializer(serializers.ModelSerializer):
    owner = serializers.EmailField(source="owner.email", read_only=True)
    services = ServiceSerializer(many=True, read_only=True)

    class Meta:
        model = Business
        fields = [
            "id",
            "slug",
            "name",
            "description",
            "timezone",
            "address",
            "phone",
            "is_active",
            "owner",
            "services",
            "created_at",
        ]
        read_only_fields = ["id", "slug", "owner", "created_at"]
