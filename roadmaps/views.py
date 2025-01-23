from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin

from .models import Course, UserCourse
from .serializers import CourseSerializer, UserCourseSerializer
# from .agents.roadmap_agent import RoadmapAgent  # 이 줄을 주석 처리


class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'])
    def enroll(self, request, pk=None):
        course = self.get_object()
        user = request.user
        
        if UserCourse.objects.filter(user=user, course=course).exists():
            return Response({"detail": "이미 등록된 코스입니다."}, 
                          status=status.HTTP_400_BAD_REQUEST)
            
        user_course = UserCourse.objects.create(
            user=user,
            course=course,
            status='enrolled'
        )
        
        serializer = UserCourseSerializer(user_course)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def complete_topic(self, request, pk=None):
        course = self.get_object()
        user_course = get_object_or_404(UserCourse, user=request.user, course=course)
        topic_id = request.data.get('topic_id')
        
        if topic_id:
            completed_topics = user_course.get_completed_topics_list()
            if topic_id not in completed_topics:
                completed_topics.append(topic_id)
                user_course.completed_topics = ','.join(map(str, completed_topics))
                user_course.update_progress()
                
        return Response({
            'progress': user_course.progress,
            'completed_topics': user_course.get_completed_topics_list()
        })


class CourseListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        courses = Course.objects.filter(is_active=True)
        user_courses = UserCourse.objects.filter(user=request.user)
        
        # 진행률 정보와 토픽 완료 상태 추가
        for course in courses:
            user_course = user_courses.filter(course=course).first()
            course.user_progress = user_course.progress if user_course else 0
            course.is_enrolled = bool(user_course)
            
            # 각 토픽의 완료 상태 확인
            completed_topics = user_course.get_completed_topics_list() if user_course else []
            for topic in course.topics:
                topic['is_completed'] = topic['id'] in completed_topics
        
        context = {
            'courses': courses,
            'user_courses': user_courses,
            'progress_percentage': user_courses.first().progress if user_courses.exists() else 0,
        }
        
        return render(request, 'roadmaps/course-list.html', context)
