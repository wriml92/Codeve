from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RoadmapViewSet, CourseListView

router = DefaultRouter()
router.register(r'roadmaps', RoadmapViewSet, basename='roadmap')

urlpatterns = [
    path('', include(router.urls)),
    path('courses/', CourseListView.as_view(), name='course-list'),
]
