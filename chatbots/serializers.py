from rest_framework import serializers
from .models import ChatMessage
import random


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['user', 'message', 'response', 'is_cached', 'created_at']
        read_only_fields = ['user', 'response', 'is_cached', 'created_at']

    def format_response(self, keyword, response):
        """응답 메시지 포맷팅"""
        response_formats = [
            f"{keyword}란 {response}",
            f"{keyword}는 {response}",
            f"{keyword}에 대해 설명드리면 {response}"
        ]
        return random.choice(response_formats)


class ChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(required=True, allow_blank=False)

    def validate_message(self, value):
        """메시지 유효성 검사 및 전처리"""
        if not value.strip():
            raise serializers.ValidationError("메시지가 필요합니다")
        return value.strip() 