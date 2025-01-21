from django.urls import path
from . import views

app_name = 'courses'

urlpatterns = [
    path('', views.course_list_view, name='course-list'),
    path('theory/', views.theory_lesson_view, name='theory-lesson'),
    path('theory/<str:topic_id>/', views.theory_lesson_view,
         name='theory-lesson-detail'),
    path('practice/', views.practice_view, name='practice'),
    path('practice/<str:topic_id>/', views.practice_view, name='practice-detail'),
    path('assignment/', views.assignment_view, name='assignment'),
    path('assignment/<str:topic_id>/',
         views.assignment_view, name='assignment-detail'),
    path('reflection/', views.reflection_view, name='reflection'),
    path('complete-topic/<str:topic_id>/',
         views.complete_topic, name='complete-topic'),
    path('resume-learning/', views.resume_learning, name='resume-learning'),
]
