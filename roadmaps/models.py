from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()


class Course(models.Model):
    """학습 코스 모델"""
    
    CATEGORY_CHOICES = [
        ('python_basics', 'Python 기초'),
        ('data_structures', '자료구조'),
        ('algorithms', '알고리즘'),
        ('web_dev', '웹 개발'),
        ('data_science', '데이터 사이언스'),
    ]

    name = models.CharField(
        max_length=200,
        help_text='코스의 이름'
    )
    description = models.TextField(
        help_text='코스에 대한 상세 설명'
    )
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        default='python_basics',
        help_text='코스의 카테고리'
    )
    topics = models.JSONField(
        help_text='JSON 형태의 토픽 목록'
    )
    estimated_hours = models.IntegerField(
        default=0,
        help_text='예상 학습 시간(시간)'
    )
    is_active = models.BooleanField(
        default=True,
        help_text='코스 활성화 여부'
    )
    order = models.IntegerField(
        default=0,
        help_text='커리큘럼 내 표시 순서'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return self.name

    @property
    def completion_rate(self):
        """코스의 전체 수강생 대비 완료율을 계산"""
        total_enrollments = self.user_courses.count()
        if total_enrollments == 0:
            return 0
        completed = self.user_courses.filter(status='completed').count()
        return (completed / total_enrollments) * 100


class UserCourse(models.Model):
    """사용자의 코스 수강 정보 모델"""
    
    STATUS_CHOICES = [
        ('enrolled', '수강중'),
        ('completed', '완료'),
        ('dropped', '중단')
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='roadmap_enrollments',
        help_text='수강 사용자'
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='user_courses',
        help_text='수강 중인 코스'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='enrolled',
        help_text='수강 상태'
    )
    progress = models.FloatField(
        default=0,
        help_text='진행률 (0-100)'
    )
    completed_topics = models.TextField(
        default='',
        blank=True,
        help_text='완료한 토픽 ID (쉼표로 구분)'
    )
    started_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_accessed_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'course']
        ordering = ['-last_accessed_at']

    def __str__(self):
        return f"{self.user.username}의 {self.course.name} 학습 현황"

    def get_completed_topics_list(self):
        """완료한 토픽 ID 목록을 반환"""
        if not self.completed_topics:
            return []
        return self.completed_topics.split(',')

    def update_progress(self):
        """토픽 완료 상태를 기반으로 진행률 업데이트"""
        completed_topics = self.get_completed_topics_list()
        total_topics = len(self.course.topics) * 4  # 각 토픽당 4가지 유형
        
        if total_topics > 0:
            self.progress = (len(completed_topics) / total_topics * 100)
            
            if self.progress >= 100:
                self.status = 'completed'
                
            self.save()
