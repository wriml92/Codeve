from django.shortcuts import render, redirect
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django.shortcuts import get_object_or_404
from .models import Course, Lesson, Quiz, PracticeExercise, UserCourse
from .serializers import (CourseSerializer, LessonSerializer, QuizSerializer,
                        PracticeExerciseSerializer, UserCourseSerializer)
from django.http import JsonResponse
import json
from typing import Dict, Any
import openai
from pathlib import Path
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

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

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def submit_answer(self, request, pk=None):
        quiz = self.get_object()
        answer = request.data.get('answer')
        code_input = request.data.get('code_input')

        # LLM API 호출하여 코드 실행 및 채점
        evaluation_result = evaluate_code_with_llm(code_input)

        if answer == quiz.correct_answer:
            return JsonResponse({
                'result': '정답입니다!',
                'feedback': evaluation_result['feedback'],
                'is_correct': True
            })
        return JsonResponse({
            'result': '틀렸습니다. 다시 시도해보세요.',
            'feedback': evaluation_result['feedback'],
            'is_correct': False
        })

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
        user_course = UserCourse.objects.get(user=request.user)
    except UserCourse.DoesNotExist:
        user_course = UserCourse.objects.create(
            user=request.user,
            progress=0,
            completed_topics=''
        )
    
    # 현재 완료된 토픽 목록 가져오기
    completed_topics = set(user_course.completed_topics.split(',')) if user_course.completed_topics else set()
    completed_topics.add(str(topic_id))
    
    # 중복 제거 및 정렬
    completed_topics = sorted(list(filter(None, completed_topics)))
    
    # 진행률 계산 (전체 토픽 수는 임시로 10개로 가정)
    total_topics = 10
    progress = (len(completed_topics) / total_topics) * 100
    
    # 업데이트
    user_course.completed_topics = ','.join(completed_topics)
    user_course.progress = progress
    user_course.save()
    
    return JsonResponse({
        'status': 'success',
        'message': '학습이 완료되었습니다.',
        'progress': progress
    })

def theory_lesson_view(request, topic_id='input_output'):
    # 데이터 파일 경로
    data_dir = Path(__file__).parent / 'data' / 'theory'
    file_path = data_dir / f"{topic_id}.json"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            theory_data = json.load(f)
            
        # HTML 콘텐츠에서 불필요한 백틱과 html 태그 제거
        content = theory_data['content'].replace('```html\n', '').replace('\n```', '')
            
        context = {
            'topic_name': theory_data['topic_name'],
            'content': content,
            'topic_id': topic_id
        }
    except FileNotFoundError:
        context = {
            'topic_name': '토픽을 찾을 수 없습니다',
            'content': '<p class="text-red-500">해당 토픽의 내용이 없습니다.</p>',
            'topic_id': topic_id
        }
    
    # course_list.json에서 토픽 목록 가져오기
    course_list_path = Path(__file__).parent / 'agents' / 'course_list.json'
    with open(course_list_path, 'r', encoding='utf-8') as f:
        course_list = json.load(f)
    
    # 현재 코스의 모든 토픽 가져오기 (예: python 코스)
    topics = course_list['python']['topics']
    
    # 이전 토픽 찾기
    current_index = next((i for i, topic in enumerate(topics) if topic['id'] == topic_id), -1)
    prev_topic = topics[current_index - 1] if current_index > 0 else None
    
    context.update({
        'topics': topics,  # 템플릿에 토픽 목록 전달
        'prev_topic': prev_topic  # 이전 토픽 정보 전달
    })
    
    return render(request, 'courses/theory-lesson.html', context)

def practice_view(request, topic_id='input_output'):
    # 데이터 파일 경로
    data_dir = Path(__file__).parent / 'data' / 'practice'
    file_path = data_dir / f"{topic_id}.json"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            practice_data = json.load(f)
            
        # 실습 내용만 추출
        content = practice_data.get('content', '')
        if '## 출력' in content:
            # 출력 부분만 추출하고 HTML 태그 제거
            content = content.split('## 출력')[1].split('```html')[1].split('```')[0]
            
        context = {
            'topic_name': practice_data['topic_name'],
            'content': content,
            'topic_id': topic_id
        }
    except FileNotFoundError:
        context = {
            'topic_name': '토픽을 찾을 수 없습니다',
            'content': '<p class="text-red-500">해당 토픽의 실습 내용이 없습니다.</p>',
            'topic_id': topic_id
        }
    
    # course_list.json에서 토픽 목록 가져오기
    course_list_path = Path(__file__).parent / 'agents' / 'course_list.json'
    with open(course_list_path, 'r', encoding='utf-8') as f:
        course_list = json.load(f)
    
    # 현재 코스의 모든 토픽 가져오기 (예: python 코스)
    topics = course_list['python']['topics']
    
    context.update({
        'topics': topics  # 템플릿에 토픽 목록 전달
    })
    
    return render(request, 'courses/practice.html', context)

def assignment_view(request, topic_id='input_output'):
    # 데이터 파일 경로
    data_dir = Path(__file__).parent / 'data' / 'assignment'
    file_path = data_dir / f"{topic_id}.json"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            assignment_data = json.load(f)
            
        content = assignment_data['content']
        if '## 출력' in content:
            content = content.split('## 출력')[1].split('```html')[1].split('```')[0].strip()
        
        # 각 퀴즈 분리
        quizzes = []
        quiz_parts = content.split('퀴즈')
        
        for i, part in enumerate(quiz_parts[1:], 1):
            quiz_content = part.strip()
            quiz_type = 'multiple_choice' if i == 1 else 'code'
            
            # 퀴즈 1의 경우 선택지 추출
            choices = []
            if i == 1:
                # 문제 내용과 선택지 분리
                content_lines = quiz_content.split('\n')
                question_lines = []
                in_choices = False
                
                for line in content_lines:
                    line = line.strip()
                    if line.startswith('<ol'):
                        in_choices = True
                        continue
                    elif line.startswith('</ol'):
                        in_choices = False
                        continue
                    elif in_choices and line.startswith('<li>'):
                        # <li> 태그 제거하고 선택지 텍스트만 추출
                        choice_text = line.replace('<li>', '').replace('</li>', '').strip()
                        choices.append(choice_text)
                    elif not in_choices and line:
                        question_lines.append(line)
                
                quiz_content = '\n'.join(question_lines)
            
            quizzes.append({
                'id': i,
                'content': quiz_content,
                'type': quiz_type,
                'choices': choices if i == 1 else []
            })
            
        context = {
            'topic_name': assignment_data['topic_name'],
            'quizzes': quizzes,
            'topic_id': topic_id
        }
    except FileNotFoundError:
        context = {
            'topic_name': '토픽을 찾을 수 없습니다',
            'quizzes': [],
            'topic_id': topic_id
        }
    
    # course_list.json에서 토픽 목록 가져오기
    course_list_path = Path(__file__).parent / 'agents' / 'course_list.json'
    with open(course_list_path, 'r', encoding='utf-8') as f:
        course_list = json.load(f)
    
    topics = course_list['python']['topics']
    context.update({'topics': topics})
    
    return render(request, 'courses/assignment.html', context)

def reflection_view(request):
    return render(request, 'courses/reflection.html')
def check_answer(request):
    data = json.loads(request.body)
    question_id = data.get('question_id')
    user_answer = data.get('answer')
    
    # 여기서 LLM API를 호출하여 답안을 평가
    evaluation_result = evaluate_answer(question_id, user_answer)
    
    return JsonResponse({
        'correct': evaluation_result['is_correct'],
        'feedback': evaluation_result['feedback']
    })

def course_list_view(request):
    # course_list.json에서 토픽 목록 가져오기
    course_list_path = Path(__file__).parent / 'agents' / 'course_list.json'
    with open(course_list_path, 'r', encoding='utf-8') as f:
        course_list = json.load(f)
    
    # Python 코스의 토픽 목록 가져오기
    python_course = course_list['python']
    topics = python_course['topics']
    
    # 사용자가 로그인한 경우 학습 진행률과 각 토픽의 학습 상태 계산
    if request.user.is_authenticated:
        # UserCourse에서 사용자의 학습 기록 가져오기
        user_course = UserCourse.objects.filter(user=request.user).first()
        completed_topics = set()  # 완료된 토픽 ID 저장
        
        if user_course:
            # 완료된 토픽 ID 목록 가져오기 (예: "1,2,3" -> {1,2,3})
            completed_topics = set(map(str, user_course.completed_topics.split(','))) if user_course.completed_topics else set()
            progress_percentage = user_course.progress
        else:
            progress_percentage = 0
            
        # 각 토픽에 학습 완료 상태 추가
        for topic in topics:
            topic['is_completed'] = topic['id'] in completed_topics
    else:
        progress_percentage = 0
        for topic in topics:
            topic['is_completed'] = False
    
    context = {
        'course': python_course,
        'topics': topics,
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
        return redirect('courses:theory-lesson-detail', topic_id=next_topic_id)
    else:
        # 완료한 토픽이 없으면 첫 번째 토픽으로 이동
        return redirect('courses:theory-lesson-detail', topic_id='variables')

