from django.shortcuts import render
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
    
    context.update({
        'topics': topics  # 템플릿에 토픽 목록 전달
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
            quiz_type = 'code' if i in [2, 3] else 'text'
            
            # 퀴즈 1의 경우 선택지 추출
            choices = []
            if i == 1:
                # 문제 내용과 선택지 분리
                content_lines = quiz_content.split('\n')
                for line in content_lines:
                    line = line.strip()
                    # 숫자로 시작하는 선택지만 추출
                    if line and line[0].isdigit() and '. ' in line:
                        choices.append(line)
            
            # 선택지를 제외한 문제 내용만 저장
            if i == 1:
                # 선택지 이전의 문제 설명만 저장
                question_lines = []
                for line in content_lines:
                    if line.strip() and not (line.strip()[0].isdigit() and '. ' in line):
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
    
    # 사용자가 로그인한 경우 학습 진행률 계산
    progress_percentage = 0
    if request.user.is_authenticated:
        # 여기에서 사용자의 학습 진행률을 계산하는 로직을 추가할 수 있습니다.
        pass
    
    context = {
        'course': python_course,
        'topics': topics,
        'progress_percentage': progress_percentage
    }
    
    return render(request, 'roadmaps/course-list.html', context)

