from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'chatbot', views.ChatbotViewSet, basename='chatbot')

app_name = 'chatbots'

urlpatterns = [
    path('api/', include(router.urls)),
] 