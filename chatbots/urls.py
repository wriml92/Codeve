from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ChatbotViewSet

router = DefaultRouter()
router.register(r'chatbot', ChatbotViewSet, basename='chatbot')

app_name = 'chatbots'

urlpatterns = [
    path('api/', include(router.urls)),
] 