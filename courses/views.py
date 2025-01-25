from django.shortcuts import render, redirect
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django.shortcuts import get_object_or_404
from .models import Course, Lesson, Assignment, PracticeExercise, UserCourse
from .serializers import (CourseSerializer, LessonSerializer, AssignmentSerializer,
                          PracticeExerciseSerializer, UserCourseSerializer)
from django.http import JsonResponse
import json
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
        # content 디렉토리에서 파일을 찾도록 수정
        current_file = Path(__file__).parent / 'data' / 'topics' / topic_id / 'content' / f'{content_type}.json'
        
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


@cache_page(60 * 15)  # 15분 캐싱
def theory_lesson_view(request, topic_id=None):
    """이론 학습 뷰"""
    if topic_id is None:
        topic_id = TOPICS[0]['id']
        
    topic_name = next((t['name'] for t in TOPICS if t['id'] == topic_id), '')
    
    try:
        # HTML 파일 직접 읽기
        theory_file = Path(__file__).parent / 'data' / 'topics' / topic_id / 'content' / 'theory.html'
        if theory_file.exists():
            with open(theory_file, 'r', encoding='utf-8') as f:
                content_html = f.read()
        else:
            content_html = '<p>이론 내용을 찾을 수 없습니다.</p>'
            
    except Exception as e:
        print(f"이론 내용 로드 중 오류 발생: {str(e)}")
        content_html = '<p>이론 내용을 불러오는 중 오류가 발생했습니다.</p>'
    
    # 이전/다음 토픽 찾기
    current_index = next((i for i, topic in enumerate(TOPICS) if topic['id'] == topic_id), -1)
    prev_topic = TOPICS[current_index - 1] if current_index > 0 else None
    next_topic = TOPICS[current_index + 1] if current_index < len(TOPICS) - 1 else None
    
    context = {
        'topics': TOPICS,
        'topic_id': topic_id,
        'topic_name': topic_name,
        'content': mark_safe(content_html),
        'prev_topic': prev_topic,
        'next_topic': next_topic
    }
    
    return render(request, 'courses/theory-lesson.html', context)


def practice_view(request, topic_id=None):
    """실습 뷰"""
    if topic_id is None:
        topic_id = TOPICS[0]['id']
        
    topic_name = next((t['name'] for t in TOPICS if t['id'] == topic_id), '')
    
    # HTML 파일 직접 읽기
    try:
        practice_file = Path(__file__).parent / 'data' / 'topics' / topic_id / 'content' / 'practice.html'
        if practice_file.exists():
            with open(practice_file, 'r', encoding='utf-8') as f:
                content_html = f.read()
                
                # 메타데이터와 불필요한 마크업 제거
                # HTML 주석 제거
                content_html = re.sub(r'<!--[\s\S]*?-->', '', content_html)
                # 출력 데이터 마크업 제거
                content_html = re.sub(r'#\s*출력\s*데이터\s*```html', '', content_html)
                # 모든 백틱 제거
                content_html = re.sub(r'```(?:html)?\s*', '', content_html)
                # 실제 콘텐츠 부분만 추출
                if '<div class="practice-content' in content_html:
                    content_html = re.search(r'(<div class="practice-content.*?</div>)\s*$', content_html, re.DOTALL)
                    if content_html:
                        content_html = content_html.group(1)
        else:
            content_html = '<p>실습 내용을 찾을 수 없습니다.</p>'
    except Exception as e:
        print(f"실습 내용 로드 중 오류 발생: {str(e)}")
        content_html = '<p>실습 내용을 불러오는 중 오류가 발생했습니다.</p>'
    
    context = {
        'topics': TOPICS,
        'topic_id': topic_id,
        'topic_name': topic_name,
        'practice_content': mark_safe(content_html)
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

    if not user_course or not user_course.completed_topics:
        # 학습 기록이 없으면 첫 번째 토픽으로 이동
        return redirect('courses:theory-lesson-detail', topic_id=TOPICS[0]['id'])

    # completed_topics에서 마지막으로 완료한 토픽 ID 가져오기
    completed_topics = user_course.completed_topics.split(',') if user_course.completed_topics else []
    
    if completed_topics:
        last_completed_topic = completed_topics[-1]
        # TOPICS 리스트에서 현재 토픽의 인덱스 찾기
        current_index = next((i for i, topic in enumerate(TOPICS) if topic['id'] == last_completed_topic), -1)
        
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

def assignment_view(request, topic_id=None):
    """과제 뷰"""
    if topic_id is None:
        topic_id = TOPICS[0]['id']
        
    topic_name = next((t['name'] for t in TOPICS if t['id'] == topic_id), '')
    
    try:
        # assignment.json 파일 읽기
        assignment_data = load_topic_content(topic_id, 'assignment')
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


@csrf_exempt
@require_http_methods(["POST"])
def submit_assignment(request, topic_id):
    try:
        data = json.loads(request.body)
        assignment_id = data.get('assignment_id')
        answer_type = data.get('type')
        answer = data.get('answer')

        # 과제 데이터 로드
        current_file = Path(__file__).parent / 'data' / 'topics' / topic_id / 'content' / 'assignment.json'
        with open(current_file, 'r', encoding='utf-8') as f:
            assignments = json.load(f)['assignments']

        # 해당 과제 찾기
        assignment = next((a for a in assignments if str(a['id']) == str(assignment_id)), None)
        if not assignment:
            return JsonResponse({'error': '과제를 찾을 수 없습니다.'}, status=404)

        # 과제 유형에 따른 처리
        if answer_type in ['concept', 'theory_concept', 'metaphor']:
            # 객관식 문제 처리
            is_correct = str(answer) == str(assignment['correct_answer'])
            feedback = assignment['explanation'] if is_correct else assignment['hint']
            
            return JsonResponse({
                'correct': is_correct,
                'feedback': feedback
            })
            
        elif answer_type in ['analysis', 'implementation']:
            # 코드 분석 및 구현 문제 처리
            analyzer = CodeSubmissionAnalyzer()
            
            if answer_type == 'analysis':
                # 분석 문제 평가
                result = analyzer.analyze_code_analysis(
                    submitted_analysis=answer,
                    code_to_analyze=assignment.get('code_to_analyze', ''),
                    points_to_consider=assignment.get('points_to_consider', []),
                    expected_points=assignment.get('expected_points', [])
                )
            else:
                # 구현 문제 평가
                result = analyzer.analyze_code_implementation(
                    submitted_code=answer,
                    test_cases=assignment.get('test_cases', []),
                    constraints=assignment.get('constraints', [])
                )
            
            return JsonResponse({
                'correct': result.is_correct,
                'feedback': result.feedback,
                'suggestions': result.suggestions
            })
            
        else:
            return JsonResponse({'error': '지원하지 않는 과제 유형입니다.'}, status=400)

    except json.JSONDecodeError:
        return JsonResponse({'error': '잘못된 요청 형식입니다.'}, status=400)
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


@csrf_exempt
async def submit_practice(request, topic_id):
    """실습 스크린샷 제출 및 분석"""
    if request.method != 'POST':
        return JsonResponse({'error': '잘못된 요청 방식입니다.'}, status=405)
    
    try:
        if 'screenshot' not in request.FILES:
            return JsonResponse({'error': '스크린샷이 제출되지 않았습니다.'}, status=400)
        
        screenshot = request.FILES['screenshot']
        
        # 임시 파일로 저장
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
            for chunk in screenshot.chunks():
                temp_file.write(chunk)
            temp_path = temp_file.name
        
        try:
            # 이미지 분석
            agent = PracticeAnalysisAgent()
            result = await agent.process({
                'topic_id': topic_id,
                'image_path': temp_path,
                'user_id': str(request.user.id)  # 사용자 ID 추가
            })
            
            print(f"분석 결과: {result}")  # 디버깅을 위한 로그 추가
            
            # 분석 결과에 따른 응답 생성
            if result.get('success'):
                response_data = {
                    'success': True,
                    'passed': result.get('passed', False),
                    'feedback': result.get('feedback', ''),
                    'sections': result.get('sections', {})
                }
                
                # 모든 섹션을 통과한 경우 축하 메시지 추가
                if result.get('passed'):
                    response_data['message'] = '🎉 축하합니다! 실습을 성공적으로 완료했어요!'
                
                return JsonResponse(response_data)
            else:
                print(f"분석 실패: {result.get('error')}")  # 디버깅을 위한 로그 추가
                return JsonResponse({
                    'success': False,
                    'error': result.get('error', '분석 중 오류가 발생했습니다.')
                })
                
        finally:
            # 임시 파일 삭제
            if os.path.exists(temp_path):
                os.unlink(temp_path)
                
    except Exception as e:
        import traceback
        print(f"서버 오류 발생: {str(e)}")
        print(traceback.format_exc())  # 상세한 에러 스택 트레이스 출력
        return JsonResponse({
            'success': False,
            'error': f'서버 오류가 발생했습니다: {str(e)}'
        }, status=500)
