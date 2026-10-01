from datetime import timedelta

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions, serializers, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Service
from apps.core.permissions import IsProvider

from .availability import get_available_slots
from .models import TimeOff, WorkingHours
from .serializers import (
    AvailabilityQuerySerializer,
    AvailabilitySerializer,
    TimeOffSerializer,
    WorkingHoursSerializer,
)


class OwnedByProviderViewSet(viewsets.ModelViewSet):
    """Providers manage scheduling data of their own businesses only."""

    permission_classes = [IsProvider]
    filterset_fields = ["business__slug"]

    def get_queryset(self):
        return self.model.objects.filter(business__owner=self.request.user).select_related(
            "business"
        )


class WorkingHoursViewSet(OwnedByProviderViewSet):
    model = WorkingHours
    serializer_class = WorkingHoursSerializer
    filterset_fields = ["business__slug", "weekday"]


class TimeOffViewSet(OwnedByProviderViewSet):
    model = TimeOff
    serializer_class = TimeOffSerializer


class ServiceAvailabilityView(APIView):
    """Bookable start times for a service on a given day."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        parameters=[OpenApiParameter("date", str, description="YYYY-MM-DD", required=True)],
        responses=AvailabilitySerializer,
    )
    def get(self, request, pk: int):
        service = get_object_or_404(
            Service.objects.select_related("business"),
            pk=pk,
            is_active=True,
            business__is_active=True,
        )
        query = AvailabilityQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        day = query.validated_data["date"]

        # "today" is UTC; allow one day back for businesses in time zones behind UTC.
        today = timezone.localdate()
        horizon = today + timedelta(days=settings.RESERVO_BOOKING_HORIZON_DAYS)
        if not (today - timedelta(days=1) <= day <= horizon):
            raise serializers.ValidationError(
                {"date": f"Must be between today and {horizon.isoformat()}."}
            )

        payload = {
            "service": service.pk,
            "date": day,
            "timezone": service.business.timezone,
            "slots": get_available_slots(service, day),
        }
        return Response(AvailabilitySerializer(payload).data)
