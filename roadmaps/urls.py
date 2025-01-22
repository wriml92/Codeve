from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CourseViewSet, CourseListView

router = DefaultRouter()
router.register(r'courses', CourseViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('course-list/', CourseListView.as_view(), name='course-list'),
]
