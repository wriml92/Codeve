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

    def _validate_enrollment(self, user, course):
        """코스 등록 가능 여부 검증"""
        if UserCourse.objects.filter(user=user, course=course).exists():
            return False, "이미 등록된 코스입니다."
        return True, None

    def _validate_topic_completion(self, topic_id, topic_type, course):
        """토픽 완료 처리를 위한 입력값 검증"""
        # 필수 파라미터 검증
        if not topic_id or not topic_type:
            return False, "topic_id와 topic_type은 필수입니다."

        # topic_type 검증
        valid_types = ['theory', 'practice', 'assignment', 'reflection']
        if topic_type not in valid_types:
            return False, "유효하지 않은 topic_type입니다."

        # topic_id 검증
        if not any(str(topic['id']) == str(topic_id) for topic in course.topics):
            return False, "유효하지 않은 topic_id입니다."

        return True, None

    def _complete_topic(self, user_course, topic_id, topic_type):
        """토픽 완료 처리 및 진행률 업데이트"""
        completed_topics = user_course.get_completed_topics_list()
        topic_key = f"{topic_id}_{topic_type}"

        if topic_key not in completed_topics:
            completed_topics.append(topic_key)
            user_course.completed_topics = ','.join(completed_topics)
            user_course.save()
            user_course.update_progress()

        return user_course

    @action(detail=True, methods=['post'])
    def enroll(self, request, pk=None):
        """사용자를 코스에 등록하는 API"""
        course = self.get_object()
        user = request.user

        # 등록 가능 여부 검증
        is_valid, error_message = self._validate_enrollment(user, course)
        if not is_valid:
            return Response(
                {"detail": error_message},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 코스 등록
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

        # 입력값 검증
        is_valid, error_message = self._validate_topic_completion(topic_id, topic_type, course)
        if not is_valid:
            return Response(
                {"detail": error_message},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 토픽 완료 처리
        updated_user_course = self._complete_topic(user_course, topic_id, topic_type)
        return Response(UserCourseSerializer(updated_user_course).data)


class CourseListView(ListView):
    """코스 목록을 보여주는 View"""
    model = Course
    template_name = 'roadmaps/course-list.html'
    context_object_name = 'courses'

    def get_queryset(self):
        """활성화된 코스만 조회"""
        return Course.objects.filter(is_active=True)

    def _get_user_course_data(self, user):
        """사용자의 코스 수강 정보 조회"""
        user_course = UserCourse.objects.filter(user=user).first()
        if not user_course:
            return {
                'topics': [],
                'progress_percentage': 0
            }

        serializer = UserCourseSerializer(user_course)
        return {
            'topics': serializer.get_topic_status(user_course),
            'progress_percentage': user_course.progress
        }

    def get_context_data(self, **kwargs):
        """컨텍스트 데이터 구성"""
        context = super().get_context_data(**kwargs)
        if not self.request.user.is_authenticated:
            return context

        # 사용자의 코스 수강 정보 추가
        context.update(self._get_user_course_data(self.request.user))
        return context
