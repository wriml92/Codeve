from rest_framework import serializers
from .models import ChatMessage


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['user', 'message', 'response', 'created_at']
        read_only_fields = ['user', 'response', 'created_at']


class ChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(required=True, allow_blank=False)

    def validate_message(self, value):
        """메시지 유효성 검사"""
        if not value or not value.strip():
            raise serializers.ValidationError("메시지 내용이 비어있습니다.")
        
        if len(value.strip()) < 2:
            raise serializers.ValidationError("메시지는 최소 2자 이상이어야 합니다.")
            
        if len(value.strip()) > 200:
            raise serializers.ValidationError("메시지는 200자를 초과할 수 없습니다.")
            
        return value.strip() 