from rest_framework import viewsets
from rest_framework.response import Response
from .models import ChatMessage
from .serializers import ChatMessageSerializer, ChatRequestSerializer
from openai import OpenAI
from django.conf import settings
from rest_framework.exceptions import APIException
import logging
import json
import os
import random
import re

# 로깅 설정
logger = logging.getLogger(__name__)


def load_cached_responses():
    try:
        json_path = os.path.join(os.path.dirname(__file__), 'responses.json')

        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


class ChatbotViewSet(viewsets.ViewSet):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # load_cached_responses 함수 사용
        self.cached_responses = load_cached_responses()

    def extract_keywords(self, message):
        # 특수문자 및 공백 정리
        message = re.sub(r'[^\w\s]', ' ', message)
        message = message.lower()  # 소문자 변환

        # 불용어 목록
        stop_words = ['이란', '란', '이', '가', '은', '는', '을', '를', '에',
                      '대해', '뭐야', '무엇', '설명', '해줘', '알려줘', '?', '.']

        # 단어 분리 및 불용어 제거
        words = message.split()
        keywords = [word for word in words if word not in stop_words]

        return keywords

    def find_best_match(self, keywords):
        if not keywords:
            return None

        # 1. 정확한 키워드 매칭
        for keyword in keywords:
            if keyword in self.cached_responses:
                response = self.cached_responses[keyword]
                return ChatMessageSerializer().format_response(keyword, response)

        # 2. 부분 매칭 (가장 긴 일치 키워드 찾기)
        best_match = None
        max_match_length = 0

        for keyword in keywords:
            for cache_key in self.cached_responses:
                if keyword in cache_key or cache_key in keyword:
                    match_length = len(keyword)
                    if match_length > max_match_length:
                        max_match_length = match_length
                        best_match = (
                            cache_key, self.cached_responses[cache_key])

        if best_match:
            cache_key, response = best_match
            return ChatMessageSerializer().format_response(cache_key, response)

        return None

    def create(self, request):
        # 사용자 인증 확인
        if not request.user.is_authenticated:
            return Response({"error": "로그인이 필요한 서비스입니다."}, status=401)

        # 요청 데이터 검증
        serializer = ChatRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        message = serializer.validated_data['message']

        # 1. 정확한 메시지 매칭
        if message in self.cached_responses:
            response = self.cached_responses[message]
            formatted_response = ChatMessageSerializer().format_response(message, response)
            self._save_chat_message(request.user, message, formatted_response, True)
            return Response({'response': formatted_response})

        # 2. 키워드 기반 검색
        keywords = self.extract_keywords(message)
        cached_response = self.find_best_match(keywords)

        if cached_response:
            self._save_chat_message(request.user, message, cached_response, True)
            return Response({'response': cached_response})

        # 3. OpenAI API 호출
        try:
            response_text = self._call_openai_api(message)
            self._save_chat_message(request.user, message, response_text, False)
            return Response({'response': response_text})
        except Exception as e:
            logger.error(f"API 호출 중 오류 발생: {str(e)}")
            return Response({'error': str(e)}, status=500)

    def _save_chat_message(self, user, message, response, is_cached):
        """채팅 메시지 저장"""
        try:
            chat_message = ChatMessage.objects.create(
                user=user,
                message=message,
                response=response,
                is_cached=is_cached
            )
            return chat_message
        except Exception as e:
            logger.error(f"채팅 메시지 저장 중 오류 발생: {str(e)}")
            # 메시지 저장 실패는 사용자 응답에 영향을 주지 않도록 함
            return None

    def _call_openai_api(self, message):
        # OpenAI API 키 확인
        if not settings.OPENAI_API_KEY:
            logger.error("OpenAI API 키가 설정되지 않았습니다")
            raise APIException("OpenAI API 키가 설정되지 않았습니다")

        try:
            # OpenAI API 호출
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            
            # 스트리밍 없이 일반 응답으로 변경
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": """
                        당신은 파이썬 프로그래밍 언어를 가르쳐주는 선생님입니다. 다음 규칙을 따라주세요:
                        1. 항상 존댓말을 사용합니다
                        2. 공감하는 태도로 응답합니다
                        3. 답변은 2-3문장으로 간단명료하게 합니다
                        4. 주제와 관련없는 질문은 무시합니다
                        5. 필요한 경우 추가 질문을 합니다
                    """},
                    {"role": "user", "content": message}
                ],
                temperature=0.7,
                max_tokens=500,
                stream=False  # 스트리밍 비활성화
            )

            # 응답 처리
            if not response.choices or not response.choices[0].message.content:
                logger.error("OpenAI API가 빈 응답을 반환했습니다")
                raise APIException("응답을 생성할 수 없습니다")

            return response.choices[0].message.content.strip()

        except Exception as e:
            error_msg = str(e)
            logger.error(f"OpenAI API 오류: {error_msg}")
            
            if "rate limit" in error_msg.lower():
                raise APIException("요청이 너무 많습니다. 잠시 후 다시 시도해주세요")
            elif "invalid_api_key" in error_msg.lower():
                raise APIException("API 키가 유효하지 않습니다")
            elif "model_not_found" in error_msg.lower():
                raise APIException("지원하지 않는 AI 모델입니다")
            else:
                raise APIException("챗봇 응답 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요")
