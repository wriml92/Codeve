import os
import sys
import django
import asyncio
import json
from pathlib import Path

# Django 설정을 위한 프로젝트 루트 경로 추가
project_root = str(Path(__file__).resolve().parent.parent.parent)
sys.path.append(project_root)

# Django 설정 초기화
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Codeve.settings')
django.setup()

from courses.llm.practice_llm import PracticeLLM

# course_list.json에서 토픽 리스트 가져오기
def get_all_topics():
    course_list_path = Path(__file__).parent.parent / 'data' / 'course_list.json'
    with open(course_list_path, 'r', encoding='utf-8') as f:
        course_data = json.load(f)
        return [topic['id'] for topic in course_data['python']['topics']]

# 모든 토픽 리스트
DEFAULT_TOPICS = get_all_topics()

async def generate_practice_content(topic_ids=None):
    """실습 내용 생성"""
    print("테스트 실습 내용 생성을 시작합니다...")
    
    # topic_ids가 없으면 기본 토픽 사용
    if topic_ids is None:
        topic_ids = DEFAULT_TOPICS
    elif isinstance(topic_ids, str):
        topic_ids = [topic_ids]
    
    practice_llm = PracticeLLM()
    
    for topic_id in topic_ids:
        try:
            print(f"\n[{topic_id}] 토픽의 실습 내용을 생성합니다...")
            await practice_llm.generate(topic_id)
            print(f"✅ [{topic_id}] 토픽의 실습 내용이 생성되었습니다.")
        except Exception as e:
            print(f"❌ [{topic_id}] 토픽 생성 중 오류 발생: {str(e)}")
    
    print("\n모든 테스트 실습 내용 생성이 완료되었습니다.")

def main():
    """메인 함수"""
    # 커맨드 라인 인자로 토픽 ID를 받음
    topic_ids = sys.argv[1:] if len(sys.argv) > 1 else None
    
    # 비동기 함수 실행
    asyncio.run(generate_practice_content(topic_ids))

if __name__ == "__main__":
    main() 