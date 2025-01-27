from typing import List, Dict, Any, Optional
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import ChatMessage
from .serializers import ChatMessageSerializer, ChatRequestSerializer
from openai import OpenAI
from django.conf import settings
from rest_framework.exceptions import APIException


class ChatbotViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    # OpenAI API 설정
    MODEL_NAME = "gpt-4o-mini"
    MAX_TOKENS = 1000
    TEMPERATURE = 0.2
    MAX_CONVERSATION_HISTORY = 20
    
    # 시스템 메시지
    system_message = """당신은 파이썬 프로그래밍을 가르치는 전문 교육자입니다. 다음 가이드라인을 따라 학습자를 지도해주세요:

        [응답 스타일]
        1. 친근하고 전문적인 어조로 존댓말을 사용합니다
        2. 학습자의 수준에 맞춰 설명하되, 너무 어렵거나 쉽지 않게 합니다
        3. 답변은 2-3문장으로 명확하고 간단하게 제공합니다
        4. 코드 예시가 필요한 경우, 짧고 이해하기 쉬운 예시를 제공합니다
        5. 실생활의 비유나 예시를 적극 활용해 설명합니다
        6. 긴 설명보다는 핵심을 간단히 전달하고, 필요시 추가 질문을 유도합니다
        7. 학습자가 스스로 생각할 수 있도록 힌트를 제공합니다

        [교육 내용]
        1. 파이썬 기본 문법과 개념을 설명할 때:
           - 실제 사용 사례와 함께 설명
           - 다른 언어와의 차이점 언급
           - 주의해야 할 점 강조
           - 초보자가 이해하기 쉬운 비유 사용
           - 실무에서 자주 사용되는 패턴 소개

        2. 에러나 문제해결 관련 질문:
           - 에러의 원인을 쉽게 설명
           - 구체적인 해결 방법 제시
           - 비슷한 에러를 방지하는 방법 안내
           - 디버깅 팁 제공
           - 문제해결 과정을 단계별로 설명

        3. 라이브러리나 프레임워크 관련:
           - 주요 기능과 사용 목적 설명
           - 기본적인 사용 방법 안내
           - 대체 가능한 옵션 제시
           - 실제 프로젝트 적용 사례 언급
           - 성능이나 보안 관련 주의사항 설명

        4. 코딩 스타일과 관련하여:
           - PEP 8 가이드라인 준수
           - 클린 코드 원칙 강조
           - 가독성과 유지보수성 중요성 설명
           - 네이밍 컨벤션 강조

        [제한 사항]
        1. 파이썬과 관련없는 질문은 정중히 거절합니다
        2. 불명확한 질문에는 구체적인 예시를 요청합니다
        3. 보안이나 시스템 관련 민감한 정보는 제공하지 않습니다
        4. 코드의 전체 구현보다는 핵심 개념 설명에 집중합니다
        5. 답변이 불확실한 경우 솔직히 인정하고 대안을 제시합니다

        [대화 방식]
        1. 학습자의 질문 의도를 정확히 파악합니다
        2. 필요한 경우 추가 질문으로 명확화를 요청합니다
        3. 답변 후에는 관련된 학습 방향을 제시합니다
        4. 실수하기 쉬운 부분을 미리 언급합니다
        5. 학습자가 더 깊이 이해할 수 있는 키워드나 주제를 제안합니다"""

    def create(self, request) -> Response:
        """사용자 메시지를 처리하고 응답을 생성합니다."""
        serializer = ChatRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        message = serializer.validated_data['message']
        
        try:
            response_text = self._call_openai_api(message)
            self._save_chat_message(request.user, message, response_text)
            return Response({'response': response_text})
        except APIException as e:
            return Response({'error': str(e)}, status=500)

    def _save_chat_message(self, user, message: str, response: str) -> Optional[ChatMessage]:
        """대화 내용을 데이터베이스에 저장합니다."""
        try:
            return ChatMessage.objects.create(
                user=user,
                message=message,
                response=response
            )
        except Exception:
            return None

    def _get_conversation_history(self) -> List[Dict[str, str]]:
        """이전 대화 내역을 가져와 OpenAI 메시지 형식으로 변환합니다."""
        previous_messages = ChatMessage.objects.filter(
            user=self.request.user
        ).order_by('-created_at')[:self.MAX_CONVERSATION_HISTORY][::-1]

        messages = [{"role": "system", "content": self.system_message}]
        
        for prev_msg in previous_messages:
            messages.extend([
                {"role": "user", "content": prev_msg.message},
                {"role": "assistant", "content": prev_msg.response}
            ])
            
        return messages

    def _call_openai_api(self, message: str) -> str:
        """OpenAI API를 호출하여 응답을 생성합니다."""
        if not settings.OPENAI_API_KEY:
            raise APIException("OpenAI API 키가 설정되지 않았습니다")

        try:
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            messages = self._get_conversation_history()
            messages.append({"role": "user", "content": message})
            
            response = client.chat.completions.create(
                model=self.MODEL_NAME,
                messages=messages,
                temperature=self.TEMPERATURE,
                max_tokens=self.MAX_TOKENS,
            )

            if not response.choices:
                raise APIException("AI 모델이 응답을 생성하지 못했습니다")

            return response.choices[0].message.content.strip()

        except Exception as e:
            error_msg = str(e).lower()
            if "rate limit" in error_msg:
                raise APIException("요청이 너무 많습니다. 잠시 후 다시 시도해주세요")
            elif "invalid_api_key" in error_msg:
                raise APIException("API 설정에 문제가 있습니다")
            elif "model_not_found" in error_msg:
                raise APIException("AI 모델을 찾을 수 없습니다")
            else:
                raise APIException(f"AI 응답 생성 중 오류가 발생했습니다: {str(e)}")
