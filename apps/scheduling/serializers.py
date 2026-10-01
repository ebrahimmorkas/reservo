from rest_framework import serializers

from apps.catalog.models import Business

from .models import TimeOff, WorkingHours


class OwnedBusinessField(serializers.SlugRelatedField):
    """Business slug restricted to businesses owned by the requesting user."""

    def __init__(self, **kwargs):
        super().__init__(slug_field="slug", **kwargs)

    def get_queryset(self):
        return Business.objects.filter(owner=self.context["request"].user)


class WorkingHoursSerializer(serializers.ModelSerializer):
    business = OwnedBusinessField()

    class Meta:
        model = WorkingHours
        fields = ["id", "business", "weekday", "start_time", "end_time"]

    def validate(self, attrs):
        business = attrs.get("business", getattr(self.instance, "business", None))
        weekday = attrs.get("weekday", getattr(self.instance, "weekday", None))
        start = attrs.get("start_time", getattr(self.instance, "start_time", None))
        end = attrs.get("end_time", getattr(self.instance, "end_time", None))

        if start >= end:
            raise serializers.ValidationError({"end_time": "Must be after start_time."})

        overlapping = WorkingHours.objects.filter(
            business=business, weekday=weekday, start_time__lt=end, end_time__gt=start
        )
        if self.instance:
            overlapping = overlapping.exclude(pk=self.instance.pk)
        if overlapping.exists():
            raise serializers.ValidationError("Overlaps existing working hours for this day.")
        return attrs


class TimeOffSerializer(serializers.ModelSerializer):
    business = OwnedBusinessField()

    class Meta:
        model = TimeOff
        fields = ["id", "business", "starts_at", "ends_at", "reason"]

    def validate(self, attrs):
        start = attrs.get("starts_at", getattr(self.instance, "starts_at", None))
        end = attrs.get("ends_at", getattr(self.instance, "ends_at", None))
        if start >= end:
            raise serializers.ValidationError({"ends_at": "Must be after starts_at."})
        return attrs


class AvailabilityQuerySerializer(serializers.Serializer):
    date = serializers.DateField()


class AvailabilitySerializer(serializers.Serializer):
    service = serializers.IntegerField()
    date = serializers.DateField()
    timezone = serializers.CharField()
    slots = serializers.ListField(child=serializers.DateTimeField())
