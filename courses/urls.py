from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'courses'

router = DefaultRouter()
router.register(r'courses', views.CourseViewSet)
router.register(r'lessons', views.LessonViewSet)
router.register(r'quizzes', views.QuizViewSet)
router.register(r'exercises', views.PracticeExerciseViewSet)
router.register(r'user-courses', views.UserCourseViewSet, basename='user-course')

urlpatterns = [
    path('', include(router.urls)),
    path('course-selection/', views.course_selection_view, name='course-selection'),
    path('theory-lesson/', views.theory_lesson_view, name='theory-lesson'),
    path('practice/', views.practice_view, name='practice'),
    path('assignment/', views.assignment_view, name='assignment'),
    path('reflection/', views.reflection_view, name='reflection'),
] 