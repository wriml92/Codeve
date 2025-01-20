from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin

from .models import Roadmap, UserRoadmap, RoadmapStep, Course, UserCourse
# from .agents.roadmap_agent import RoadmapAgent  # 이 줄을 주석 처리

class RoadmapViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """사용자의 로드맵 목록 조회"""
        user_roadmaps = UserRoadmap.objects.filter(user=request.user)
        data = [{
            'id': ur.roadmap.id,
            'title': ur.roadmap.title,
            'description': ur.roadmap.description,
            'progress': ur.progress,
            'current_step': ur.current_step.title if ur.current_step else None,
            'started_at': ur.started_at
        } for ur in user_roadmaps]
        return Response(data)

    def retrieve(self, request, pk=None):
        """특정 로드맵 상세 조회"""
        roadmap = get_object_or_404(Roadmap, pk=pk)
        user_roadmap = UserRoadmap.objects.filter(
            user=request.user,
            roadmap=roadmap
        ).first()
        
        steps = RoadmapStep.objects.filter(roadmap=roadmap)
        
        data = {
            'id': roadmap.id,
            'title': roadmap.title,
            'description': roadmap.description,
            'difficulty': roadmap.difficulty,
            'estimated_hours': roadmap.estimated_hours,
            'progress': user_roadmap.progress if user_roadmap else 0,
            'steps': [{
                'id': step.id,
                'title': step.title,
                'description': step.description,
                'order': step.order,
                'estimated_hours': step.estimated_hours,
                'is_current': user_roadmap.current_step == step if user_roadmap else False
            } for step in steps]
        }
        return Response(data)

    @action(detail=False, methods=['post'])
    async def generate(self, request):
        """맞춤형 로드맵 생성"""
        try:
            # 사용자 데이터로 로드맵 생성
            # agent = RoadmapAgent(request.data)
            roadmap_data = await RoadmapAgent(request.data).generate_roadmap()
            
            # 로드맵 저장
            roadmap = Roadmap.objects.create(
                title=roadmap_data['title'],
                description=roadmap_data['description'],
                difficulty=roadmap_data['difficulty'],
                estimated_hours=roadmap_data['estimated_hours']
            )
            
            # 로드맵 단계 저장
            for i, step_data in enumerate(roadmap_data['steps'], 1):
                RoadmapStep.objects.create(
                    roadmap=roadmap,
                    title=step_data['title'],
                    description=step_data['description'],
                    order=i,
                    estimated_hours=step_data['estimated_hours']
                )
            
            # 사용자-로드맵 연결
            UserRoadmap.objects.create(
                user=request.user,
                roadmap=roadmap
            )
            
            return Response({
                'message': '로드맵이 생성되었습니다.',
                'roadmap_id': roadmap.id
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def progress(self, request, pk=None):
        """로드맵 진행 상태 업데이트"""
        roadmap = get_object_or_404(Roadmap, pk=pk)
        user_roadmap = get_object_or_404(
            UserRoadmap,
            user=request.user,
            roadmap=roadmap
        )
        
        step_id = request.data.get('step_id')
        if step_id:
            step = get_object_or_404(RoadmapStep, pk=step_id)
            user_roadmap.current_step = step
            user_roadmap.progress = (step.order / roadmap.steps.count()) * 100
            user_roadmap.save()
            
        return Response({
            'message': '진행 상태가 업데이트되었습니다.',
            'progress': user_roadmap.progress
        })

class CourseListView(LoginRequiredMixin, ListView):
    model = Course
    template_name = 'roadmaps/course-list.html'
    context_object_name = 'courses'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 사용자의 코스 진행 상황 조회
        user_courses = UserCourse.objects.filter(user=self.request.user)
        progress_dict = {uc.course_id: uc.progress for uc in user_courses}
        
        # 각 코스에 대한 진행률 추가
        for course in context['courses']:
            course.progress = progress_dict.get(course.id, 0)
            
            # topics JSON 데이터를 템플릿에서 사용할 수 있도록 변환
            if isinstance(course.topics, str):
                import json
                course.topics = json.loads(course.topics)
                
        return context
