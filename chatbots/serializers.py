from rest_framework import serializers
from .models import ChatMessage
import random
import re


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['user', 'message', 'response', 'is_cached', 'created_at']
        read_only_fields = ['user', 'response', 'is_cached', 'created_at']

    def format_response(self, keyword, response):
        """응답 메시지 포맷팅"""
        # 응답이 이미 키워드로 시작하는 경우
        if response.startswith(keyword):
            return response

        # 응답에 키워드가 포함되어 있지 않은 경우
        if keyword not in response:
            response_formats = [
                f"{keyword}란 {response}",
                f"{keyword}는 {response}",
                f"{keyword}에 대해 설명드리면 {response}"
            ]
            return random.choice(response_formats)
            
        return response


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

    @staticmethod
    def extract_keyword(message):
        """메시지에서 핵심 키워드 추출"""
        # 특수문자 제거 및 소문자 변환
        cleaned = re.sub(r'[^\w\s]', '', message).lower().strip()
        
        # 불용어 리스트
        stop_words = ['이란', '란', '이', '가', '은', '는', '을', '를', '에',
                     '대해', '뭐야', '무엇', '설명', '해줘', '알려줘']
        
        # 불용어 제거
        for word in stop_words:
            cleaned = cleaned.replace(word, '')
            
        return cleaned.strip() 