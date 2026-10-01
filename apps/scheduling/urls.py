from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ServiceAvailabilityView, TimeOffViewSet, WorkingHoursViewSet

router = DefaultRouter()
router.register("working-hours", WorkingHoursViewSet, basename="working-hours")
router.register("time-off", TimeOffViewSet, basename="time-off")

urlpatterns = [
    path(
        "services/<int:pk>/availability/",
        ServiceAvailabilityView.as_view(),
        name="service-availability",
    ),
    *router.urls,
]
