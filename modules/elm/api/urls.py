from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ELMDataViewSet

router = DefaultRouter()
router.register(r'data', ELMDataViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
