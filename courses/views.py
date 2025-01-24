from django.shortcuts import render, redirect
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django.shortcuts import get_object_or_404
from .models import Course, Lesson, Quiz, PracticeExercise, UserCourse, TheoryContent
from .serializers import (CourseSerializer, LessonSerializer, QuizSerializer,
                          PracticeExerciseSerializer, UserCourseSerializer)
from django.http import JsonResponse
import json
from typing import Dict, Any
import openai
from pathlib import Path
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.utils.safestring import mark_safe
from .llm.theory_llm import TheoryLLM
from asgiref.sync import sync_to_async, async_to_sync
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .agents.analysis_agent import AnalysisAgent
from .llm.assignment_llm import AssignmentLLM
from django.views.decorators.cache import cache_page


# 공통으로 사용할 토픽 목록을 모듈 레벨에 정의
TOPICS = [
    {'id': 'input_output', 'name': '입출력'},
    {'id': 'variables', 'name': '변수'},
    {'id': 'strings', 'name': '문자열'},
    {'id': 'lists', 'name': '리스트'},
    {'id': 'tuples', 'name': '튜플'},
    {'id': 'dictionaries', 'name': '딕셔너리'},
    {'id': 'conditionals', 'name': '조건문'},
    {'id': 'loops', 'name': '반복문'},
    {'id': 'functions', 'name': '함수'},
    {'id': 'classes', 'name': '클래스'},
    {'id': 'modules', 'name': '모듈'},
    {'id': 'exceptions', 'name': '예외처리'},
    {'id': 'files', 'name': '파일 입출력'}
]

class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def enroll(self, request, pk=None):
        course = self.get_object()
        user = request.user

        if UserCourse.objects.filter(user=user, course=course).exists():
            return Response({'error': '이미 수강 신청된 강좌입니다.'},
                            status=status.HTTP_400_BAD_REQUEST)

        user_course = UserCourse.objects.create(
            user=user,
            course=course,
            status='enrolled'
        )

        serializer = UserCourseSerializer(user_course)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class LessonViewSet(viewsets.ModelViewSet):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        course_id = self.kwargs.get('course_pk')
        if course_id:
            return Lesson.objects.filter(course_id=course_id)
        return Lesson.objects.all()


class QuizViewSet(viewsets.ModelViewSet):
    queryset = Quiz.objects.all()
    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class PracticeExerciseViewSet(viewsets.ModelViewSet):
    queryset = PracticeExercise.objects.all()
    serializer_class = PracticeExerciseSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def submit_solution(self, request, pk=None):
        exercise = self.get_object()
        submitted_code = request.data.get('code')

        # TODO: 코드 실행 및 테스트 케이스 검증 로직 구현
        return Response({'message': '제출이 완료되었습니다.'})


class UserCourseViewSet(viewsets.ModelViewSet):
    serializer_class = UserCourseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserCourse.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def update_progress(self, request, pk=None):
        user_course = self.get_object()
        progress = request.data.get('progress_percentage')

        if progress is not None:
            user_course.progress_percentage = progress
            if progress == 100:
                user_course.status = 'completed'
            elif progress > 0:
                user_course.status = 'in_progress'
            user_course.save()

            serializer = self.get_serializer(user_course)
            return Response(serializer.data)

        return Response({'error': '진행률이 제공되지 않았습니다.'},
                        status=status.HTTP_400_BAD_REQUEST)


@login_required
@require_POST
def complete_topic(request, topic_id):
    try:
        # 현재 토픽이 유효한지 확인
        if not any(topic['id'] == topic_id for topic in TOPICS):
            return JsonResponse({
                'status': 'error',
                'message': '유효하지 않은 토픽입니다.'
            }, status=400)
        
        # 코스 가져오기 또는 생성
        try:
            course = Course.objects.first()
            if not course:
                course = Course.objects.create(
                    title='Python 기초 프로그래밍',
                    description='Python 프로그래밍의 기초를 배우는 코스입니다.',
                    difficulty='beginner',
                    estimated_hours=40
                )
        except Exception as e:
            print(f"코스 생성 중 오류: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': '코스 생성 중 오류가 발생했습니다.'
            }, status=500)
        
        try:
            # 사용자의 코스 등록 정보 찾기 또는 생성
            user_course, created = UserCourse.objects.get_or_create(
                user=request.user,
                course=course,
                defaults={
                    'status': 'enrolled',
                    'progress': 0,
                    'completed_topics': ''
                }
            )
        except Exception as e:
            print(f"사용자 코스 생성 중 오류: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': '사용자 코스 생성 중 오류가 발생했습니다.'
            }, status=500)

        try:
            # 현재 완료된 토픽 목록 가져오기
            completed_topics = set(user_course.completed_topics.split(',')) if user_course.completed_topics else set()
            completed_topics.add(str(topic_id))

            # 중복 제거 및 정렬
            completed_topics = sorted(list(filter(None, completed_topics)))

            # 진행률 계산 (TOPICS 리스트의 길이 사용)
            progress = (len(completed_topics) / len(TOPICS)) * 100

            # 업데이트
            user_course.completed_topics = ','.join(completed_topics)
            user_course.progress = progress
            if progress >= 100:
                user_course.status = 'completed'
            user_course.save()
        except Exception as e:
            print(f"진행률 업데이트 중 오류: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': '진행률 업데이트 중 오류가 발생했습니다.'
            }, status=500)

        return JsonResponse({
            'status': 'success',
            'message': '학습이 완료되었습니다.',
            'progress': progress,
            'completed_topics': completed_topics
        })
        
    except Exception as e:
        print(f"예상치 못한 오류: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'서버 오류가 발생했습니다: {str(e)}'
        }, status=500)


def load_topic_content(topic_id: str, content_type: str) -> dict:
    """토픽의 현재 버전 콘텐츠 로드"""
    try:
        theory_llm = TheoryLLM()
        # content 디렉토리에서 파일을 찾도록 수정
        current_file = theory_llm.data_dir / topic_id / 'content' / f'{content_type}.json'
        
        if current_file.exists():
            with open(current_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    except Exception as e:
        print(f"콘텐츠 로드 중 오류 발생: {str(e)}")
        return None


@cache_page(60 * 15)  # 15분 동안 캐시
def topic_view(request, topic_id):
    """토픽 뷰"""
    context = {
        'topics': TOPICS,
        'topic_id': topic_id
    }
    return render(request, 'courses/topic.html', context)


async def theory_lesson_view(request, topic_id=None):
    """이론 학습 뷰"""
    if topic_id is None:
        topic_id = TOPICS[0]['id']
        
    topic_name = next((t['name'] for t in TOPICS if t['id'] == topic_id), '')
    
    # DB에서 내용 가져오기
    try:
        theory_content = await sync_to_async(TheoryContent.objects.get)(topic_id=topic_id)
        content_html = theory_content.content
    except TheoryContent.DoesNotExist:
        # 없으면 생성
        theory_llm = TheoryLLM()
        content_html = await theory_llm.generate(topic_id)
    
    context = {
        'topics': TOPICS,
        'topic_id': topic_id,
        'topic_name': topic_name,
        'content': mark_safe(content_html)
    }
    
    return await sync_to_async(render)(request, 'courses/theory-lesson.html', context)


def practice_view(request, topic_id=None):
    """실습 뷰"""
    if topic_id is None:
        topic_id = TOPICS[0]['id']
        
    topic_name = next((t['name'] for t in TOPICS if t['id'] == topic_id), '')
    content = load_topic_content(topic_id, 'practice')
    
    if content:
        content_html = content['content']
        content_html = mark_safe(content_html)  # HTML 안전하게 렌더링
    else:
        content_html = ''
    
    context = {
        'topics': TOPICS,
        'topic_id': topic_id,
        'topic_name': topic_name,
        'content': content_html
    }
    
    return render(request, 'courses/practice.html', context)


def reflection_view(request):
    return render(request, 'courses/reflection.html')


def course_list_view(request):
    """코스 목록 뷰"""
    # course_list.json에서 코스 정보 가져오기
    course_list_path = Path(__file__).parent / 'data' / 'course_list.json'
    with open(course_list_path, 'r', encoding='utf-8') as f:
        course_list = json.load(f)

    # Python 코스 정보에 정의된 토픽 목록 사용
    python_course = course_list['python']
    python_course['topics'] = TOPICS  # 정의된 토픽 목록으로 교체

    # 사용자가 로그인한 경우 학습 진행률 계산
    progress_percentage = 0
    if request.user.is_authenticated:
        try:
            user_course = UserCourse.objects.get(user=request.user)
            completed_topics = set(user_course.completed_topics.split(',')) if user_course.completed_topics else set()
            progress_percentage = (len(completed_topics) / len(TOPICS)) * 100
            
            # 각 토픽의 완료 상태 설정
            for topic in TOPICS:
                topic['is_completed'] = topic['id'] in completed_topics
        except UserCourse.DoesNotExist:
            # 학습 기록이 없는 경우
            for topic in TOPICS:
                topic['is_completed'] = False
    else:
        # 비로그인 사용자
        for topic in TOPICS:
            topic['is_completed'] = False

    context = {
        'course': python_course,
        'topics': TOPICS,
        'progress_percentage': progress_percentage
    }

    return render(request, 'roadmaps/course-list.html', context)


@login_required
def resume_learning(request):
    # 사용자의 마지막 학습 상태 확인
    user_course = UserCourse.objects.filter(user=request.user).first()

    if not user_course:
        # 학습 기록이 없으면 코스 목록 페이지로 이동
        return redirect('courses:course-list')

    # completed_topics에서 마지막으로 완료한 토픽 ID 가져오기
    completed_topics = user_course.completed_topics.split(',') if user_course.completed_topics else []

    if completed_topics:
        # 마지막으로 완료한 토픽의 다음 토픽으로 이동
        last_completed_topic = completed_topics[-1]
        # 여기서는 토픽 ID가 순차적으로 증가한다고 가정
        next_topic_id = str(int(last_completed_topic) + 1)
        return redirect('courses:theory-detail', topic_id=next_topic_id)
    else:
        # 완료한 토픽이 없으면 첫 번째 토픽으로 이동
        return redirect('courses:theory-detail', topic_id='variables')


def load_assignment_data(topic_id: str) -> dict:
    """토픽별 과제 데이터 로드"""
    try:
        base_dir = Path(__file__).parent
        assignment_file = base_dir / 'data' / 'topics' / topic_id / 'content' / 'assignment.json'
        
        with open(assignment_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # 파일이 없을 경우 기본 템플릿 반환
        return {
            "assignments": [
                {
                    "id": 1,
                    "type": "concept",
                    "content": "문제를 준비 중입니다.",
                    "choices": ["준비 중", "준비 중", "준비 중", "준비 중"]
                },
                {
                    "id": 2,
                    "type": "analysis",
                    "content": "문제를 준비 중입니다."
                },
                {
                    "id": 3,
                    "type": "implementation",
                    "content": "문제를 준비 중입니다."
                }
            ]
        }

async def assignment_view(request, topic_id=None):
    """과제 뷰"""
    if topic_id is None:
        topic_id = TOPICS[0]['id']
        
    topic_name = next((t['name'] for t in TOPICS if t['id'] == topic_id), '')
    
    try:
        # assignment.json 파일 읽기
        assignment_data = load_topic_content(topic_id, 'assignment')
        
        if assignment_data is None:  # 파일이 없거나 로드 실패
            context = {
                'topics': TOPICS,
                'topic_id': topic_id,
                'topic_name': topic_name,
                'content': mark_safe('<div class="alert alert-warning">과제 내용을 준비 중입니다.</div>')
            }
        else:
            context = {
                'topics': TOPICS,
                'topic_id': topic_id,
                'topic_name': topic_name,
                'content': mark_safe(assignment_data['content'])
            }
        
        return await sync_to_async(render)(request, 'courses/assignment.html', context)
        
    except Exception as e:
        print(f"Error loading assignment content: {str(e)}")
        context = {
            'topics': TOPICS,
            'topic_id': topic_id,
            'topic_name': topic_name,
            'content': mark_safe('<div class="alert alert-danger">과제 내용을 불러오는데 실패했습니다.</div>')
        }
        return await sync_to_async(render)(request, 'courses/assignment.html', context)


@csrf_exempt
async def submit_assignment(request):
    """과제 제출 처리"""
    if request.method != 'POST':
        return JsonResponse({'error': '잘못된 요청 방식입니다.'}, status=405)
    
    try:
        data = json.loads(request.body)
        assignment_id = data.get('assignment_id')
        assignment_type = data.get('assignment_type')
        answer = data.get('answer')
        topic_id = data.get('topic_id')
        
        if not all([assignment_id, assignment_type, answer, topic_id]):
            return JsonResponse({'error': '필수 데이터가 누락되었습니다.'}, status=400)
        
        # 답안 분석
        agent = AnalysisAgent()
        result = await agent.analyze(assignment_type, answer, assignment_id, topic_id)
        
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({'error': f'서버 오류가 발생했습니다: {str(e)}'}, status=500)


def save_assignment_data(topic_id: str, data: Dict[str, Any]) -> None:
    """과제 데이터 저장"""
    base_dir = Path(__file__).parent
    assignment_file = base_dir / 'data' / 'topics' / topic_id / 'content' / 'assignment.json'
    
    # 디렉토리가 없으면 생성
    assignment_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(assignment_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
