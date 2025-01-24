from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CourseViewSet, CourseListView

# DRF 라우터 설정
router = DefaultRouter()
router.register('courses', CourseViewSet)

# URL 패턴 정의
urlpatterns = [
    path('', include(router.urls)),
    path('course-list/', CourseListView.as_view(), name='course-list'),
]
