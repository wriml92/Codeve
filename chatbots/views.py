from rest_framework import viewsets
from rest_framework.response import Response
from .models import ChatMessage
from openai import OpenAI
from django.conf import settings
from rest_framework.exceptions import APIException
import logging
import json
import os

# 로깅 설정
logger = logging.getLogger(__name__)

class ChatbotViewSet(viewsets.ViewSet):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # cached_responses.json 파일 로드
        json_path = os.path.join(os.path.dirname(__file__), 'cached_responses.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            self.cached_responses = json.load(f)

    def create(self, request):
        # 클라이언트로부터 메시지 받기
        message = request.data.get('message')
        if not message:
            return Response({'error': '메시지가 필요합니다'}, status=400)

        # 캐시된 응답 확인
        if message in self.cached_responses:
            response_text = self.cached_responses[message]
            ChatMessage.objects.create(
                user=request.user,
                message=message,
                response=response_text,
                is_cached=True
            )
            return Response({'response': response_text})

        # OpenAI API 키 확인
        if not settings.OPENAI_API_KEY:
            raise APIException("OpenAI API key is not configured")
        
        try:
            # OpenAI API 호출
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-4o-mini", #gpt-3.5-turbo, gpt-4로도 변경가능
                messages=[
                    # 시스템 프롬프트 설정
                    {"role": "system", "content": """
                        당신은 전문 상담원입니다. 다음 규칙을 따라주세요:
                        1. 항상 존댓말을 사용합니다
                        2. 공감하는 태도로 응답합니다
                        3. 답변은 2-3문장으로 간단명료하게 합니다
                        4. 필요한 경우 추가 질문을 합니다
                    """},
                    {"role": "user", "content": message}
                ],
                temperature=0.1,  # 응답의 창의성 조절
                max_tokens=200,   # 최대 토큰 수 제한
                frequency_penalty=0.5  # 반복 표현 방지
            )
            
            # API 응답 처리 및 저장
            response_text = response.choices[0].message.content
            used_model = response.model  # 사용된 모델 정보

            # 모델 정보와 함께 로그 기록
            logger.info(f"사용된 모델: {used_model}")

            ChatMessage.objects.create(
                user=request.user,
                message=message,
                response=response_text,
                is_cached=False
            )
            
            return Response({'response': response_text, 'model': used_model})
            
        except Exception as e:
            # 오류 로깅 및 에러 응답
            logger.error(f"API 호출 중 오류 발생: {str(e)}")
            return Response({'error': str(e)}, status=500)