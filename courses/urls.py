from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# API 라우터 설정
router = DefaultRouter()
router.register(r'courses', views.CourseViewSet)
router.register(r'lessons', views.LessonViewSet)
router.register(r'quizzes', views.QuizViewSet)
router.register(r'exercises', views.PracticeExerciseViewSet)
router.register(r'user-courses', views.UserCourseViewSet, basename='user-course')

app_name = 'courses'

urlpatterns = [
    # API URLs
    path('api/', include(router.urls)),
    
    # Web URLs
    path('', views.course_list_view, name='course-list'),
    path('theory/', views.theory_lesson_view, name='theory-lesson'),
    path('theory/<str:topic_id>/', views.theory_lesson_view, name='theory-lesson-detail'),
    path('practice/', views.practice_view, name='practice'),
    path('practice/<str:topic_id>/', views.practice_view, name='practice-detail'),
    path('assignment/', views.assignment_view, name='assignment'),
    path('assignment/<str:topic_id>/', views.assignment_view, name='assignment-detail'),
    path('reflection/', views.reflection_view, name='reflection'),
    path('complete-topic/<str:topic_id>/', views.complete_topic, name='complete-topic'),
    path('resume-learning/', views.resume_learning, name='resume-learning'),
]
