import json
import os

def load_cached_responses():
    try:
        # JSON 파일 경로 설정
        json_path = os.path.join(os.path.dirname(__file__), 'cached_responses.json')
        
        # JSON 파일 읽기
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # 기본 응답들
        return {
            "안녕하세요": "안녕하세요! 무엇을 도와드릴까요?",
            "감사합니다": "천만에요! 다른 문의사항이 있으시다면 언제든 말씀해주세요."
        } 