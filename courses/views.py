from django.shortcuts import render, redirect
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django.shortcuts import get_object_or_404
from .models import Course, Lesson, Assignment, PracticeExercise, UserCourse
from .serializers import (CourseSerializer, LessonSerializer, AssignmentSerializer,
                        PracticeExerciseSerializer, UserCourseSerializer)
from django.http import JsonResponse, HttpResponse
import json
import os
import tempfile
from typing import Dict, Any
from pathlib import Path
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils.safestring import mark_safe
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt
import re
from asgiref.sync import sync_to_async
from .scripts.assignment_tools import AssignmentDataManager, CodeSubmissionAnalyzer, CodeAnalysisResult
from .llm.practice_llm import PracticeAnalysisAgent
from .agents.assignment_analysis_agent import AssignmentAnalysisAgent
from datetime import datetime
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import UploadedFile
from PIL import Image
import io


# 공통으로 사용할 토픽 목록을 모듈 레벨에 정의
TOPICS = [
    {'id': 'input_output', 'name': '입력과 출력'},
    {'id': 'print', 'name': 'print() 함수'},
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


class AssignmentViewSet(viewsets.ModelViewSet):
    queryset = Assignment.objects.all()
    serializer_class = AssignmentSerializer


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
            completed_topics = set(user_course.completed_topics.split(
                ',')) if user_course.completed_topics else set()
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
    """토픽의 콘텐츠 로드"""
    try:
        # content 디렉토리에서 파일을 찾도록 수정
        content_file = Path(__file__).parent / 'data' / 'topics' / \
            topic_id / 'content' / f'{content_type}.json'

        if content_file.exists():
            with open(content_file, 'r', encoding='utf-8') as f:
                return json.load(f)

        # 파일이 없을 경우 기본 템플릿 반환
        if content_type == 'assignment':
            return {
                "assignments": [
                    {
                        "id": 1,
                        "type": "concept",
                        "content": "문제를 준비 중입니다.",
                        "choices": ["준비 중", "준비 중", "준비 중", "준비 중"]
                    }
                ]
            }
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


@cache_page(60 * 15)  # 15분 캐싱
def theory_lesson_detail(request, topic_id=None):
    """이론 학습 뷰"""
    if topic_id is None:
        topic_id = TOPICS[0]['id']

    topic_name = next((t['name'] for t in TOPICS if t['id'] == topic_id), '')

    try:
        # 새로운 경로 구조에 맞게 수정
        base_dir = Path(__file__).parent
        theory_file = base_dir / 'data' / 'topics' / \
            topic_id / 'content' / 'theory' / 'theory.html'

        with open(theory_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        context = {
            'topics': TOPICS,
            'topic_id': topic_id,
            'topic_name': topic_name,
            'content': mark_safe(content)
        }
        return render(request, 'courses/theory-lesson.html', context)

    except FileNotFoundError:
        context = {
            'topics': TOPICS,
            'topic_id': topic_id,
            'topic_name': topic_name,
            'content': mark_safe('<div class="alert alert-warning">이론 내용을 준비 중입니다.</div>')
        }
        return render(request, 'courses/theory-lesson.html', context)
    except Exception as e:
        print(f"Error loading theory content: {str(e)}")
        context = {
            'topics': TOPICS,
            'topic_id': topic_id,
            'topic_name': topic_name,
            'content': mark_safe('<div class="alert alert-danger">이론 내용을 불러오는데 실패했습니다.</div>')
        }
        return render(request, 'courses/theory-lesson.html', context)


def practice_view(request, topic_id=None):
    """실습 뷰"""
    if topic_id is None:
        topic_id = TOPICS[0]['id']

    topic_name = next((t['name'] for t in TOPICS if t['id'] == topic_id), '')

    try:
        # 새로운 경로 구조에 맞게 수정
        base_dir = Path(__file__).parent
        practice_file = base_dir / 'data' / 'topics' / \
            topic_id / 'content' / 'practice' / 'practice.html'

        with open(practice_file, 'r', encoding='utf-8') as f:
            content = f.read()

            # 메타데이터와 불필요한 마크업 제거
            content = re.sub(r'<!--[\s\S]*?-->', '', content)  # HTML 주석 제거
            content = re.sub(r'#\s*출력\s*데이터\s*```html',
                             '', content)  # 출력 데이터 마크업 제거
            content = re.sub(r'```(?:html)?\s*', '', content)  # 모든 백틱 제거

            # 실제 콘텐츠 부분만 추출
            if '<div class="practice-content' in content:
                content_match = re.search(
                    r'(<div class="practice-content.*?</div>)\s*$', content, re.DOTALL)
                if content_match:
                    content = content_match.group(1)
            
        context = {
            'topics': TOPICS,
            'topic_id': topic_id,
            'topic_name': topic_name,
            'practice_content': mark_safe(content)
        }
        return render(request, 'courses/practice.html', context)

    except FileNotFoundError:
        context = {
            'topics': TOPICS,
            'topic_id': topic_id,
            'topic_name': topic_name,
            'practice_content': mark_safe('<div class="alert alert-warning">실습 내용을 준비 중입니다.</div>')
        }
        return render(request, 'courses/practice.html', context)
    except Exception as e:
        print(f"Error loading practice content: {str(e)}")
        context = {
            'topics': TOPICS,
            'topic_id': topic_id,
            'topic_name': topic_name,
            'practice_content': mark_safe('<div class="alert alert-danger">실습 내용을 불러오는데 실패했습니다.</div>')
        }
        return render(request, 'courses/practice.html', context)


def reflection_view(request):
    return render(request, 'courses/reflection.html')


def course_list_view(request):
    """코스 목록 뷰"""
    try:
        # 기본 Python 코스 정보 정의
        python_course = {
            'id': 'python',
            'title': 'Python 기초 프로그래밍',
            'description': 'Python 프로그래밍의 기초를 배우는 코스입니다.',
            'difficulty': 'beginner',
            'estimated_hours': 40,
            'topics': TOPICS
        }

        # 사용자가 로그인한 경우 학습 진행률 계산
        progress_percentage = 0
        if request.user.is_authenticated:
            try:
                user_course = UserCourse.objects.get(
                    user=request.user,
                    course__title='Python 기초 프로그래밍'
                )
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

    except Exception as e:
        print(f"코스 목록 로드 중 오류 발생: {str(e)}")
        return render(request, 'roadmaps/course-list.html', {
            'error': '코스 정보를 불러오는 중 오류가 발생했습니다.',
            'topics': TOPICS,
            'progress_percentage': 0
        })


@login_required
def resume_learning(request):
    # 사용자의 마지막 학습 상태 확인
    user_course = UserCourse.objects.filter(user=request.user).first()

    if not user_course or not user_course.completed_topics:
        # 학습 기록이 없으면 첫 번째 토픽으로 이동
        return redirect('courses:theory-lesson-detail', topic_id=TOPICS[0]['id'])

    # completed_topics에서 마지막으로 완료한 토픽 ID 가져오기
    completed_topics = user_course.completed_topics.split(
        ',') if user_course.completed_topics else []

    if completed_topics:
        last_completed_topic = completed_topics[-1]
        # TOPICS 리스트에서 현재 토픽의 인덱스 찾기
        current_index = next((i for i, topic in enumerate(
            TOPICS) if topic['id'] == last_completed_topic), -1)

        if current_index >= len(TOPICS) - 1:
            # 마지막 토픽이면 첫 번째 토픽으로 이동
            next_topic_id = TOPICS[0]['id']
        else:
            # 다음 토픽으로 이동
            next_topic_id = TOPICS[current_index + 1]['id']

        return redirect('courses:theory-lesson-detail', topic_id=next_topic_id)
    else:
        # 완료한 토픽이 없으면 첫 번째 토픽으로 이동
        return redirect('courses:theory-lesson-detail', topic_id=TOPICS[0]['id'])


def load_assignment_data(topic_id: str) -> dict:
    """토픽별 과제 데이터 로드"""
    try:
        base_dir = Path(__file__).parent
        assignment_file = base_dir / 'data' / 'topics' / topic_id / \
            'content' / 'assignments' / 'data' / 'assignment.json'

        with open(assignment_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # 파일이 없을 경우 기본 템플릿 반환
        return {
            "assignments": [
                {
                    "id": 1,
                    "type": "concept_basic",
                    "content": "문제를 준비 중입니다.",
                    "choices": ["준비 중", "준비 중", "준비 중", "준비 중"]
                }
            ]
        }


def assignment_view(request, topic_id=None):
    """과제 뷰"""
    if topic_id is None:
        topic_id = TOPICS[0]['id']

    topic_name = next((t['name'] for t in TOPICS if t['id'] == topic_id), '')

    try:
        # assignment.json 파일 읽기
        assignment_data = load_assignment_data(topic_id)
        print(f"로드된 과제 데이터: {assignment_data}")  # 디버깅용 출력

        if assignment_data is None:  # 파일이 없거나 로드 실패
            context = {
                'topics': TOPICS,
                'topic_id': topic_id,
                'topic_name': topic_name,
                'content': mark_safe('<div class="alert alert-warning">과제 내용을 준비 중입니다.</div>'),
                'assignments': []
            }
        else:
            context = {
                'topics': TOPICS,
                'topic_id': topic_id,
                'topic_name': topic_name,
                'assignments': assignment_data.get('assignments', [])
            }

        return render(request, 'courses/assignment.html', context)

    except Exception as e:
        print(f"Error loading assignment content: {str(e)}")
        context = {
            'topics': TOPICS,
            'topic_id': topic_id,
            'topic_name': topic_name,
            'content': mark_safe('<div class="alert alert-danger">과제 내용을 불러오는데 실패했습니다.</div>'),
            'assignments': []
        }
        return render(request, 'courses/assignment.html', context)


def async_login_required(view_func):
    """비동기 뷰를 위한 로그인 필수 데코레이터"""
    async def wrapped_view(request, *args, **kwargs):
        try:
            # 세션과 유저 정보를 비동기적으로 확인
            is_authenticated = await sync_to_async(lambda r: r.user.is_authenticated)(request)
            if not is_authenticated:
                return HttpResponse(
                    '<script>window.location.href = "/accounts/login/";</script>',
                    content_type='text/html'
                )
            return await view_func(request, *args, **kwargs)
        except Exception as e:
            print(f"인증 확인 중 오류 발생: {str(e)}")
            return HttpResponse(
                '<script>window.location.href = "/accounts/login/";</script>',
                content_type='text/html'
            )
    return wrapped_view

@sync_to_async
def async_json_response(data, status=200):
    """비동기 컨텍스트에서 안전한 JsonResponse"""
    return JsonResponse(data, status=status)

@async_login_required
@csrf_exempt
@require_POST
async def submit_practice(request, topic_id):
    """실습 제출 처리"""
    print("\n=== 실습 제출 처리 시작 ===")
    print(f"Topic ID: {topic_id}")
    print(f"Request method: {request.method}")
    print(f"Request FILES: {request.FILES}")
    
    temp_file_path = None
    try:
        # 사용자 ID 가져오기
        try:
            print("사용자 ID 가져오기 시도...")
            user_id = await get_user_id_from_request(request)
            print(f"가져온 사용자 ID: {user_id}")
        except Exception as e:
            print(f"사용자 ID 가져오기 실패: {str(e)}")
            return await async_json_response({
                'success': False,
                'error': '사용자 인증이 필요합니다.'
            }, status=401)

        # 이미지 파일 가져오기
        print("이미지 파일 가져오기 시도...")
        image_file = await get_file_from_request(request, 'screenshot')
        print(f"이미지 파일 객체: {image_file}")
        if not image_file:
            print("이미지 파일이 제공되지 않음")
            return await async_json_response({
                'success': False,
                'error': '이미지가 제공되지 않았습니다.'
            }, status=400)

        # 임시 파일로 저장
        print("임시 파일 저장 시도...")
        temp_file_path = os.path.join(tempfile.gettempdir(), f'practice_{user_id}_{topic_id}.png')
        print(f"임시 파일 경로: {temp_file_path}")
        await save_file_chunks(image_file, temp_file_path)
        print("임시 파일 저장 완료")

        try:
            print("분석 에이전트 초기화 및 처리 시작...")
            # 분석 에이전트 초기화 및 처리
            agent = PracticeAnalysisAgent()
            result = await agent.process({
                'topic_id': topic_id,
                'image_path': temp_file_path,
                'user_id': user_id
            })
            print(f"분석 결과: {result}")

            # 임시 파일 삭제
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                print("임시 파일 삭제 완료")

            return await async_json_response(result)

        except Exception as e:
            print(f"분석 처리 중 오류 발생: {str(e)}")
            # 오류 발생 시 임시 파일 삭제 시도
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                print("오류 발생으로 인한 임시 파일 삭제")
            raise e

    except Exception as e:
        print(f"실습 제출 처리 중 오류 발생: {str(e)}")
        print(f"오류 상세: {type(e).__name__}")
        import traceback
        print(f"스택 트레이스:\n{traceback.format_exc()}")
        
        # 마지막으로 임시 파일 삭제 시도
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
                print("최종 임시 파일 삭제 완료")
            except:
                print("최종 임시 파일 삭제 실패")
        return await async_json_response({
            'success': False,
            'error': f'서버 오류가 발생했습니다: {str(e)}'
        }, status=500)


# 동기 작업을 위한 헬퍼 함수들
@sync_to_async
def get_user_id_from_request(request) -> str:
    """request에서 user id를 가져오는 동기 함수"""
    try:
        print(f"get_user_id_from_request 호출됨: {request.user}")
        if not hasattr(request, '_cached_user'):
            request._cached_user = request.user
        return str(request._cached_user.id)
    except Exception as e:
        print(f"사용자 ID 가져오기 실패: {str(e)}")
        raise

@sync_to_async
def get_file_from_request(request, field_name: str) -> UploadedFile:
    """request.FILES에서 파일을 가져오는 동기 함수"""
    print(f"get_file_from_request 호출됨: field_name={field_name}")
    file = request.FILES.get(field_name)
    print(f"가져온 파일 객체: {file}")
    return file

@sync_to_async
def save_file_chunks(file_obj: UploadedFile, temp_file_path: str) -> None:
    """파일을 임시 파일로 저장하는 동기 함수"""
    print(f"save_file_chunks 시작: {temp_file_path}")
    try:
        # 이미지 파일을 PIL Image로 열기
        image = Image.open(io.BytesIO(file_obj.read()))
        
        # RGBA 모드인 경우 RGB로 변환
        if image.mode in ('RGBA', 'LA'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1])
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')
            
        # PNG 형식으로 저장
        image.save(temp_file_path, 'PNG')
        print(f"이미지 변환 및 저장 완료: {image.format} -> PNG")
    except Exception as e:
        print(f"이미지 변환 중 오류 발생: {str(e)}")
        raise
    print("save_file_chunks 완료")

@async_login_required
@csrf_exempt
@require_POST
async def submit_assignment(request, topic_id):
    """과제 제출 처리"""
    try:
        print("\n=== 과제 제출 처리 시작 ===")
        print(f"Topic ID: {topic_id}")
        print(f"Request method: {request.method}")
        print(f"Request body: {request.body}")
        
        # 요청 데이터 파싱
        try:
            data = json.loads(request.body)
            assignment_type = data.get('type')
            answer = data.get('answer')
            assignment_id = data.get('assignment_id')
            
            print(f"과제 유형: {assignment_type}")
            print(f"답안: {answer}")
            print(f"과제 ID: {assignment_id}")
            
            if not all([assignment_type, answer, assignment_id]):
                return await async_json_response({
                    'success': False,
                    'error': '필수 파라미터가 누락되었습니다.'
                }, status=400)
                
        except json.JSONDecodeError as e:
            print(f"JSON 파싱 오류: {str(e)}")
            return await async_json_response({
                'success': False,
                'error': '잘못된 요청 형식입니다.'
            }, status=400)

        # 사용자 ID 가져오기
        try:
            print("사용자 ID 가져오기 시도...")
            user_id = await get_user_id_from_request(request)
            print(f"가져온 사용자 ID: {user_id}")
        except Exception as e:
            print(f"사용자 ID 가져오기 실패: {str(e)}")
            return await async_json_response({
                'success': False,
                'error': '사용자 인증이 필요합니다.'
            }, status=401)

        # 과제 분석 에이전트 초기화 및 처리
        try:
            print("분석 에이전트 초기화 및 처리 시작...")
            agent = AssignmentAnalysisAgent()
            result = await agent.process({
                'assignment_type': assignment_type,
                'answer': answer,
                'assignment_id': assignment_id,
                'topic_id': topic_id,
                'user_id': user_id
            })
            print(f"분석 결과: {result}")
            
            return await async_json_response({
                'success': True,
                **result
            })
            
        except Exception as e:
            print(f"분석 처리 중 오류 발생: {str(e)}")
            import traceback
            print(f"상세 오류:\n{traceback.format_exc()}")
            return await async_json_response({
                'success': False,
                'error': f'과제 분석 중 오류가 발생했습니다: {str(e)}'
            }, status=500)

    except Exception as e:
        print(f"과제 제출 처리 중 오류 발생: {str(e)}")
        print(f"오류 상세: {type(e).__name__}")
        import traceback
        print(f"스택 트레이스:\n{traceback.format_exc()}")
        return await async_json_response({
            'success': False,
            'error': f'서버 오류가 발생했습니다: {str(e)}'
        }, status=500)