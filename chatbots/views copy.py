from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import ChatMessage
from .serializers import ChatMessageSerializer, ChatRequestSerializer
from openai import OpenAI
from django.conf import settings
from rest_framework.exceptions import APIException
import json
import os


def load_cached_responses():
    try:
        json_path = os.path.join(os.path.dirname(__file__), 'responses.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


class ChatbotViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cached_responses = load_cached_responses()

    def create(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        message = serializer.validated_data['message']
        keyword = ChatRequestSerializer.extract_keyword(message)
        
        # JSON 캐시 확인
        if keyword in self.cached_responses:
            response = ChatMessageSerializer().format_response(keyword, self.cached_responses[keyword])
            self._save_chat_message(request.user, message, response, True)
            return Response({'response': response})

        # OpenAI API 호출
        try:
            response_text = self._call_openai_api(message)
            self._save_chat_message(request.user, message, response_text, False)
            return Response({'response': response_text})
        except APIException as e:
            return Response({'error': str(e)}, status=500)

    def _save_chat_message(self, user, message, response, is_cached):
        try:
            return ChatMessage.objects.create(
                user=user,
                message=message,
                response=response,
                is_cached=is_cached
            )
        except Exception:
            return None

    def _call_openai_api(self, message):
        if not settings.OPENAI_API_KEY:
            raise APIException("OpenAI API 키가 설정되지 않았습니다")

        try:
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            
            # 이전 대화 내용 가져오기 (최근 5개)
            previous_messages = ChatMessage.objects.filter(
                user=self.request.user
            ).order_by('-created_at')[:5][::-1]  # 시간순 정렬

            # 시스템 메시지와 이전 대화 내용을 포함한 메시지 구성
            messages = [
                {"role": "system", "content": """
                    당신은 파이썬 프로그래밍을 가르치는 전문 교육자입니다. 다음 가이드라인을 따라 학습자를 지도해주세요:

                    [응답 스타일]
                    1. 친근하고 전문적인 어조로 존댓말을 사용합니다
                    2. 학습자의 수준에 맞춰 설명하되, 너무 어렵거나 쉽지 않게 합니다
                    3. 답변은 2-3문장으로 명확하고 간단하게 제공합니다
                    4. 코드 예시가 필요한 경우, 짧고 이해하기 쉬운 예시를 제공합니다

                    [교육 내용]
                    1. 파이썬 기본 문법과 개념을 설명할 때:
                       - 실제 사용 사례와 함께 설명
                       - 다른 언어와의 차이점 언급
                       - 주의해야 할 점 강조

                    2. 에러나 문제해결 관련 질문:
                       - 에러의 원인 설명
                       - 구체적인 해결 방법 제시
                       - 비슷한 에러를 방지하는 방법 안내

                    3. 라이브러리나 프레임워크 관련:
                       - 주요 기능과 사용 목적 설명
                       - 기본적인 사용 방법 안내
                       - 대체 가능한 옵션 제시

                    [제한 사항]
                    1. 파이썬과 관련없는 질문은 정중히 거절합니다
                    2. 불명확한 질문에는 구체적인 예시를 요청합니다
                    3. 보안이나 시스템 관련 민감한 정보는 제공하지 않습니다
                    4. 코드의 전체 구현보다는 핵심 개념 설명에 집중합니다
                """}
            ]

            # 이전 대화 내용 추가
            for prev_msg in previous_messages:
                messages.extend([
                    {"role": "user", "content": prev_msg.message},
                    {"role": "assistant", "content": prev_msg.response}
                ])

            # 현재 메시지 추가
            messages.append({"role": "user", "content": message})
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.2,
                max_tokens=1000,
            )

            if not response.choices:
                raise APIException("응답을 생성할 수 없습니다")

            return response.choices[0].message.content.strip()

        except Exception as e:
            if "rate limit" in str(e).lower():
                raise APIException("잠시 후 다시 시도해주세요")
            raise APIException("응답을 생성할 수 없습니다")
