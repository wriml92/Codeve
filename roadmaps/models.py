from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()


class Course(models.Model):
    """학습 코스 모델"""
    name = models.CharField(max_length=200)
    description = models.TextField()
    topics = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class UserCourse(models.Model):
    """사용자의 코스 수강 정보 모델"""
    STATUS_CHOICES = [
        ('enrolled', '수강중'),
        ('completed', '완료'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='roadmap_enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='user_courses')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='enrolled')
    progress = models.FloatField(default=0)
    completed_topics = models.TextField(default='', blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'course']
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.user.username}의 {self.course.name} 학습 현황"

    def get_completed_topics_list(self):
        """완료한 토픽 ID 목록을 반환"""
        if not self.completed_topics:
            return []
        return [topic.strip() for topic in self.completed_topics.split(',') if topic.strip()]

    def update_progress(self):
        """토픽 완료 상태를 기반으로 진행률 업데이트"""
        if not self.course.topics:  # 토픽이 없는 경우
            self.progress = 0
            self.save()
            return
            
        completed_topics = self.get_completed_topics_list()
        total_topics = len(self.course.topics) * 4  # 각 토픽당 4가지 유형
        completed_count = 0
        
        # 각 토픽의 각 타입별로 완료 여부 확인
        for topic in self.course.topics:
            topic_id = str(topic['id'])
            for topic_type in ['theory', 'practice', 'assignment', 'reflection']:
                topic_key = f"{topic_id}_{topic_type}"
                if topic_key in completed_topics:
                    completed_count += 1
        
        # 진행률을 정수로 계산 (소수점 버림)
        self.progress = int((completed_count / total_topics) * 100)
        
        # 모든 토픽이 완료되었을 때만 상태를 completed로 변경
        if completed_count == total_topics:
            self.status = 'completed'
        else:
            self.status = 'enrolled'
            
        self.save()
