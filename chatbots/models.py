from django.db import models
from django.conf import settings


class ChatMessage(models.Model):
    """사용자와 AI 간의 대화 내용을 저장하는 모델"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        help_text="대화를 나눈 사용자"
    )
    message = models.TextField(help_text="사용자의 질문 내용")
    response = models.TextField(help_text="AI의 응답 내용")
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="대화가 생성된 시간"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = '대화 내용'
        verbose_name_plural = '대화 내용들'

    def __str__(self):
        return f"{self.user.username}의 대화 ({self.created_at.strftime('%Y-%m-%d %H:%M')})"


class CachedResponse(models.Model):
    question_hash = models.CharField(max_length=64, unique=True)
    question = models.TextField()
    response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)