from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from django.views.decorators.csrf import csrf_exempt

# API 라우터 설정
router = DefaultRouter()
router.register(r'courses', views.CourseViewSet)
router.register(r'lessons', views.LessonViewSet)
router.register(r'assignments', views.AssignmentViewSet)
router.register(r'exercises', views.PracticeExerciseViewSet)
router.register(r'user-courses', views.UserCourseViewSet, basename='user-course')

app_name = 'courses'

urlpatterns = [
    # API URLs - 'api/' 경로로 시작
    path('api/v1/', include(router.urls)),
    
    # Web URLs
    path('', views.course_list_view, name='course-list'),
    path('theory/', views.theory_lesson_detail, name='theory-lesson'),
    path('theory/<str:topic_id>/', views.theory_lesson_detail, name='theory-lesson-detail'),
    path('practice/', views.practice_view, name='practice'),
    path('practice/<str:topic_id>/', views.practice_view, name='practice-detail'),
    path('practice/<str:topic_id>/submit/', csrf_exempt(views.submit_practice), name='submit-practice'),
    
    # 과제 관련 URL - 순서 중요
    path('assignment/submit/<str:topic_id>/', csrf_exempt(views.submit_assignment), name='submit-assignment'),
    path('assignment/<str:topic_id>/', views.assignment_view, name='assignment-detail'),
    path('assignment/', views.assignment_view, name='assignment'),
    
    path('reflection/', views.reflection_view, name='reflection'),
    path('complete-topic/<str:topic_id>/', views.complete_topic, name='complete-topic'),
    path('resume-learning/', views.resume_learning, name='resume-learning'),
]
