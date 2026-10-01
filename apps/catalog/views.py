from django.db.models import Prefetch, Q
from rest_framework import permissions, viewsets

from apps.core.permissions import IsOwnerOrReadOnly, IsProvider

from .filters import ServiceFilter
from .models import Business, Service
from .serializers import BusinessSerializer, ServiceSerializer


class ProviderWritePermissionsMixin:
    """Anyone may read; only providers may create; only owners may modify."""

    def get_permissions(self):
        if self.action == "create":
            return [IsProvider()]
        if self.action in {"update", "partial_update", "destroy"}:
            return [permissions.IsAuthenticated(), IsOwnerOrReadOnly()]
        return [permissions.AllowAny()]


def visible_to(user, active_q: Q, owner_q: Q) -> Q:
    """Active records are public; owners also see their inactive ones."""
    return active_q | owner_q if user.is_authenticated else active_q


class BusinessViewSet(ProviderWritePermissionsMixin, viewsets.ModelViewSet):
    serializer_class = BusinessSerializer
    lookup_field = "slug"
    owner_field = "owner"
    search_fields = ["name", "description", "address"]
    ordering_fields = ["name", "created_at"]
    filterset_fields = ["timezone"]

    def get_queryset(self):
        user = self.request.user
        services = Service.objects.filter(
            visible_to(user, Q(is_active=True), Q(business__owner_id=user.pk))
        )
        return (
            Business.objects.filter(visible_to(user, Q(is_active=True), Q(owner_id=user.pk)))
            .select_related("owner")
            .prefetch_related(Prefetch("services", queryset=services))
        )

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class ServiceViewSet(ProviderWritePermissionsMixin, viewsets.ModelViewSet):
    serializer_class = ServiceSerializer
    owner_field = "business.owner"
    filterset_class = ServiceFilter
    search_fields = ["name", "description", "business__name"]
    ordering_fields = ["price", "duration_minutes", "name"]

    def get_queryset(self):
        user = self.request.user
        return Service.objects.filter(
            visible_to(
                user,
                Q(is_active=True, business__is_active=True),
                Q(business__owner_id=user.pk),
            )
        ).select_related("business")
