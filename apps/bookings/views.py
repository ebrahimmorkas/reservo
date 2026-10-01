from drf_spectacular.utils import extend_schema
from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from . import services
from .filters import BookingFilter
from .models import Booking
from .serializers import BookingSerializer, CancelSerializer, RescheduleSerializer


class BookingViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Customers see their own bookings; providers also see bookings for their businesses."""

    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_class = BookingFilter
    ordering_fields = ["starts_at", "created_at"]

    def get_queryset(self):
        return (
            Booking.objects.visible_to(self.request.user)
            .select_related("service", "business", "customer")
            .order_by("-starts_at")
        )

    def perform_create(self, serializer):
        data = serializer.validated_data
        serializer.instance = services.create_booking(
            customer=self.request.user,
            service=data["service"],
            starts_at=data["starts_at"],
            notes=data.get("notes", ""),
        )

    @extend_schema(request=CancelSerializer, responses=BookingSerializer)
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        booking = self.get_object()
        payload = CancelSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        booking = services.cancel_booking(
            booking=booking, actor=request.user, reason=payload.validated_data.get("reason", "")
        )
        return Response(self.get_serializer(booking).data)

    @extend_schema(request=RescheduleSerializer, responses=BookingSerializer)
    @action(detail=True, methods=["post"])
    def reschedule(self, request, pk=None):
        booking = self.get_object()
        payload = RescheduleSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        booking = services.reschedule_booking(
            booking=booking, starts_at=payload.validated_data["starts_at"], actor=request.user
        )
        return Response(self.get_serializer(booking).data)

    @extend_schema(request=None, responses=BookingSerializer)
    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        return self._record_outcome(Booking.Status.COMPLETED)

    @extend_schema(request=None, responses=BookingSerializer)
    @action(detail=True, methods=["post"], url_path="no-show")
    def no_show(self, request, pk=None):
        return self._record_outcome(Booking.Status.NO_SHOW)

    def _record_outcome(self, status):
        booking = self.get_object()
        if booking.business.owner_id != self.request.user.pk:
            raise PermissionDenied("Only the business owner can record outcomes.")
        booking = services.mark_outcome(booking=booking, status=status)
        return Response(self.get_serializer(booking).data)
