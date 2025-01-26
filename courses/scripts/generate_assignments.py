"""
과제 생성 스크립트

특정 토픽의 과제를 생성하는 스크립트입니다.
이론과 실습 내용을 참고하여 과제를 생성합니다.

유효한 토픽 목록(VALID_TOPICS)은 courses/config/constants.py의 TOPICS 리스트를 참조합니다:
- input_output: 입출력
- print: print() 함수
- variables: 변수
- strings: 문자열
- lists: 리스트
- tuples: 튜플
- dictionaries: 딕셔너리
- conditionals: 조건문
- loops: 반복문
- functions: 함수
- classes: 클래스
- modules: 모듈
- exceptions: 예외처리
- files: 파일 입출력

루트 디렉토리에서 실행할때는 courses/scripts/generate_assignments.py 로 실행해야 합니다.

사용법:
1. 특정 토픽 과제 생성(예시:변수):
   python generate_assignments.py variables

2. 여러 토픽 과제 생성:
   python generate_assignments.py variables strings lists

3. 모든 토픽 과제 생성:
   python generate_assignments.py all

4. 특정 과제 유형만 생성:
   python generate_assignments.py variables --types concept_basic concept_application
"""

import os
import sys
from pathlib import Path
import argparse

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, project_root)

# Django 설정 초기화 (이론 내용 참조를 위해 필요)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Codeve.settings')
import django
django.setup()

import asyncio
from dotenv import load_dotenv
from courses.llm.assignment_llm import AssignmentLLM
from courses.config.constants import TOPICS

# 유효한 토픽 목록
VALID_TOPICS = [topic['id'] for topic in TOPICS]

async def generate_assignment(topics: list[str], assignment_types: list[str] = None):
    """과제 생성"""
    # 모든 토픽이 유효한지 확인
    invalid_topics = [topic for topic in topics if topic != 'all' and topic not in VALID_TOPICS]
    if invalid_topics:
        print(f"❌ 잘못된 토픽 ID: {', '.join(invalid_topics)}")
        print(f"사용 가능한 토픽: {', '.join(VALID_TOPICS)}")
        return

    # .env 파일에서 API 키 로드
    load_dotenv()
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY가 설정되지 않았습니다.")
        return

    # 생성할 토픽 목록 결정
    topics_to_generate = VALID_TOPICS if 'all' in topics else topics
    
    for topic in topics_to_generate:
        print(f"\n=== {topic} 과제 생성 시작 ===")
        try:
            # 현재 작업 디렉토리 기준으로 content_dir 설정
            if os.path.basename(os.getcwd()) == 'courses':
                base_dir = Path(os.getcwd()).parent
            else:
                base_dir = Path(os.getcwd())
            
            content_dir = base_dir / 'courses' / 'data' / 'topics' / topic / 'content'
            content_dir.mkdir(parents=True, exist_ok=True)
            
            llm = AssignmentLLM(api_key)
            if assignment_types:
                llm.assignment_types = assignment_types
            await llm.generate(topic)
            print(f"✅ {topic} 과제 생성 완료")
            
            # 파일 생성 확인
            for file_name in ['assignment.html', 'assignment.json', 'assignment_answers.json']:
                file_path = content_dir / file_name
                if file_path.exists():
                    print(f"- {file_name} 생성됨 ({file_path.stat().st_size:,} bytes)")
                
        except Exception as e:
            print(f"❌ {topic} 과제 생성 중 오류 발생: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='과제 생성 스크립트')
    parser.add_argument('topics', nargs='+', help='생성할 토픽 ID 목록 또는 "all"')
    parser.add_argument('--types', nargs='+', help='생성할 과제 유형 목록')
    args = parser.parse_args()
    
    asyncio.run(generate_assignment(args.topics, args.types)) 