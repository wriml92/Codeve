from django.shortcuts import get_object_or_404
from django.views.generic import ListView
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Course, UserCourse
from .serializers import CourseSerializer, UserCourseSerializer


class CourseViewSet(viewsets.ModelViewSet):
    """코스 관련 API를 처리하는 ViewSet"""
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'])
    def enroll(self, request, pk=None):
        """사용자를 코스에 등록하는 API"""
        course = self.get_object()
        user = request.user
        
        if UserCourse.objects.filter(user=user, course=course).exists():
            return Response(
                {"detail": "이미 등록된 코스입니다."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        user_course = UserCourse.objects.create(
            user=user,
            course=course,
            status='enrolled'
        )
        
        return Response(UserCourseSerializer(user_course).data)

    @action(detail=True, methods=['post'])
    def complete_topic(self, request, pk=None):
        """토픽 완료 처리 API"""
        course = self.get_object()
        user_course = get_object_or_404(UserCourse, user=request.user, course=course)
        topic_id = request.data.get('topic_id')
        topic_type = request.data.get('topic_type')
        
        if not topic_id or not topic_type:
            return Response(
                {"detail": "topic_id와 topic_type은 필수입니다."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        completed_topics = user_course.get_completed_topics_list()
        topic_key = f"{topic_id}_{topic_type}"
        
        if topic_key not in completed_topics:
            completed_topics.append(topic_key)
            user_course.completed_topics = ','.join(map(str, completed_topics))
            user_course.update_progress()
                
        return Response({
            'progress': user_course.progress,
            'completed_topics': user_course.get_completed_topics_list()
        })


class CourseListView(ListView):
    """코스 목록을 보여주는 View"""
    model = Course
    template_name = 'roadmaps/course-list.html'
    context_object_name = 'courses'
    
    def get_queryset(self):
        return Course.objects.filter(is_active=True)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if not self.request.user.is_authenticated:
            return context

        user_courses = UserCourse.objects.filter(user=self.request.user)
        
        for course in context['courses']:
            user_course = user_courses.filter(course=course).first()
            course.user_progress = user_course.progress if user_course else 0
            course.is_enrolled = bool(user_course)
            
            if user_course:
                completed_topics = user_course.get_completed_topics_list()
                self._process_course_topics(course, completed_topics)
        
        context.update({
            'user_courses': user_courses,
            'progress_percentage': user_courses.first().progress if user_courses.exists() else 0
        })
        
        return context
    
    def _process_course_topics(self, course, completed_topics):
        """코스 토픽의 완료 상태를 처리하는 헬퍼 메서드"""
        topic_types = ['theory', 'practice', 'assignment', 'reflection']
        for topic in course.topics:
            topic['completed_types'] = [
                t_type for t_type in topic_types 
                if f"{topic['id']}_{t_type}" in completed_topics
            ]
            topic['is_completed'] = len(topic['completed_types']) == len(topic_types)
