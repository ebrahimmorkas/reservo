from rest_framework.routers import DefaultRouter

from .views import BusinessViewSet, ServiceViewSet

router = DefaultRouter()
router.register("businesses", BusinessViewSet, basename="business")
router.register("services", ServiceViewSet, basename="service")

urlpatterns = router.urls
