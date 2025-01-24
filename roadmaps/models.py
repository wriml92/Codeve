from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()


class Course(models.Model):
    CATEGORY_CHOICES = [
        ('python_basics', 'Python 기초'),
        ('data_structures', '자료구조'),
        ('algorithms', '알고리즘'),
        ('web_dev', '웹 개발'),
        ('data_science', '데이터 사이언스'),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        default='python_basics'
    )
    topics = models.JSONField()  # JSON 형태로 토픽 목록 저장
    estimated_hours = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)  # 커리큘럼 내에서의 순서

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return self.name

    @property
    def completion_rate(self):
        total_enrollments = self.user_courses.count()
        if total_enrollments == 0:
            return 0
        completed = self.user_courses.filter(status='completed').count()
        return (completed / total_enrollments) * 100


class UserCourse(models.Model):
    STATUS_CHOICES = [
        ('enrolled', '수강중'),
        ('completed', '완료'),
        ('dropped', '중단')
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, 
                           on_delete=models.CASCADE, 
                           related_name='roadmap_enrollments')
    course = models.ForeignKey(Course, 
                             on_delete=models.CASCADE, 
                             related_name='user_courses')
    status = models.CharField(max_length=20, 
                            choices=STATUS_CHOICES, 
                            default='enrolled')
    progress = models.FloatField(default=0)  # 진행률 (0-100)
    completed_topics = models.TextField(default='', blank=True)  # 완료한 토픽 ID들을 쉼표로 구분하여 저장
    started_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_accessed_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'course']
        ordering = ['-last_accessed_at']

    def __str__(self):
        return f"{self.user.username}'s progress in {self.course.name}"

    def get_completed_topics_list(self):
        if not self.completed_topics:
            return []
        return self.completed_topics.split(',')

    def update_progress(self):
        """토픽 완료 상태를 기반으로 진행률 업데이트"""
        completed_topics = self.get_completed_topics_list()
        total_topics = len(self.course.topics) * 4  # 각 토픽당 4가지 유형 (이론, 실습, 과제, 회고)
        completed_count = len(completed_topics)
        
        self.progress = (completed_count / total_topics * 100) if total_topics > 0 else 0
        
        # 모든 토픽이 완료되었다면 코스 상태를 '완료'로 변경
        if self.progress >= 100:
            self.status = 'completed'
            
        self.save()
