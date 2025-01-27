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
        if not value or not value.strip():
            raise serializers.ValidationError("메시지 내용이 비어있습니다.")
        
        # 최소 길이 검사
        if len(value.strip()) < 2:
            raise serializers.ValidationError("메시지는 최소 2자 이상이어야 합니다.")
            
        # 최대 길이 검사
        if len(value.strip()) > 1000:
            raise serializers.ValidationError("메시지는 1000자를 초과할 수 없습니다.")
            
        return value.strip() 