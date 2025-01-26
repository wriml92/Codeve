"""
Python 교육 플랫폼 CLI 도구

이 스크립트는 교육 플랫폼의 관리를 위한 명령행 인터페이스(CLI)를 제공합니다.
과제 생성, 데이터 관리, 통계 확인 등 다양한 관리 작업을 수행할 수 있습니다.

주요 기능:
1. 콘텐츠 생성 (generate)
   - 이론 내용 생성: python cli.py generate --type theory --topic <topic_id>
   - 실습 내용 생성: python cli.py generate --type practice --topic <topic_id>
   - 과제 내용 생성: python cli.py generate --type assignment --topic <topic_id>
   - 모든 내용 생성: python cli.py generate --type all --topic <topic_id>
   - 강제 재생성: --force 또는 -f 옵션 추가

2. 과제 관리 (assignment)
   - 새로운 과제 생성: python cli.py assignment create <topic_id>
   - 과제 목록 조회: python cli.py assignment list
   - 과제 삭제: python cli.py assignment delete <topic_id>

3. 통계 관리 (stats)
   - 제출 현황 확인: python cli.py stats show <topic_id>
   - 통계 초기화: python cli.py stats reset

4. 데이터 관리 (data)
   - 데이터 백업: python cli.py data backup
   - 데이터 검증: python cli.py data verify

사용 가능한 토픽 ID:
- input_output
- print
- variables
- strings
- lists
- tuples
- dictionaries
- conditionals
- loops
- functions
- classes
- modules
- exceptions
- files

생성되는 파일 위치:
1. 이론 내용: /courses/data/topics/<topic_id>/content/theory/theory.html
2. 실습 내용: /courses/data/topics/<topic_id>/content/practice/practice.html
3. 과제 내용: 
   - /courses/data/topics/<topic_id>/content/assignments/data/assignment.json
   - /courses/data/topics/<topic_id>/content/assignments/answers/assignment_answers.json
   - /courses/data/topics/<topic_id>/content/assignments/ui/assignment.html

주의사항:
- OpenAI API 키가 .env 파일에 OPENAI_API_KEY로 설정되어 있어야 함
- 모든 명령은 courses/scripts 디렉토리에서 실행해야 함
- 생성된 콘텐츠는 검토 후 사용 권장
- 대규모 생성 시 API 비용 고려 필요
"""

import os
import sys
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, project_root)

# Django 설정 초기화
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Codeve.settings')

import django
django.setup()

import click
import asyncio  # asyncio import 추가
from typing import List
from courses.llm import ContentGenerator
from courses.llm.theory_llm import TheoryLLM
from courses.llm.practice_llm import PracticeLLM
from courses.llm.assignment_llm import AssignmentLLM
from courses.config.constants import TOPICS
from courses.llm.reflection_llm import ReflectionLLM
import json

@click.group()
def cli():
    """Codeve 콘텐츠 관리 CLI"""
    pass

@cli.command()
@click.option('--type', '-t', 
              type=click.Choice(['theory', 'practice', 'assignment', 'all']),
              default='all',
              help='생성할 콘텐츠 유형')
@click.option('--topic', help='특정 토픽 ID (옵션)')
@click.option('--force', '-f', is_flag=True, help='기존 파일 덮어쓰기')
def generate(type, topic, force):
    """콘텐츠 생성"""
    generator = ContentGenerator()
    if topic:
        asyncio.run(generator.generate_topic(topic, type, force))
    else:
        asyncio.run(generator.generate_all(type, force))

@cli.command()
@click.option('--topic', help='특정 토픽 ID (옵션)')
def init(topic):
    """과제 템플릿 초기화"""
    generator = ContentGenerator()
    generator.initialize_templates(topic)

@cli.command()
def validate():
    """생성된 콘텐츠 검증"""
    base_dir = Path(__file__).parent.parent
    course_list_path = base_dir / 'data' / 'course_list.json'
    
    with open(course_list_path, 'r', encoding='utf-8') as f:
        course_list = json.load(f)
    generator = ContentGenerator()
    generator.validate_content()

# 유효한 토픽 목록
VALID_TOPICS = [topic['id'] for topic in TOPICS]

# 유효한 콘텐츠 타입 - ContentGenerator에서 동적으로 가져오기
VALID_TYPES = ContentGenerator.get_content_types()

async def generate_content(content_type: str, topic_id: str = None):
    """콘텐츠 생성"""
    # 콘텐츠 타입 검증
    if content_type not in VALID_TYPES:
        print(f"❌ 잘못된 콘텐츠 타입: {content_type}")
        print(f"사용 가능한 타입: {', '.join(VALID_TYPES)}")
        return

    # 토픽 ID 검증
    if topic_id and topic_id not in VALID_TOPICS:
        print(f"❌ 잘못된 토픽 ID: {topic_id}")
        print(f"사용 가능한 토픽: {', '.join(VALID_TOPICS)}")
        return

    # 토픽 ID가 없으면 모든 토픽에 대해 생성
    topics_to_generate = [topic_id] if topic_id else VALID_TOPICS

    for topic in topics_to_generate:
        print(f"\n=== {topic} 콘텐츠 생성 시작 ===")
        try:
            if content_type == 'theory':
                llm = TheoryLLM()
                content = await llm.generate(topic)
                print(f"✅ {topic} 이론 내용 생성 완료")
                
            elif content_type == 'practice':
                llm = PracticeLLM()
                content = await llm.generate(topic)
                print(f"✅ {topic} 실습 내용 생성 완료")
                
            else:  # assignment
                llm = AssignmentLLM()
                result = await llm.generate(topic)
                if isinstance(result, dict) and 'content' in result:
                    content = result['content']
                else:
                    content = result
                print(f"✅ {topic} 과제 내용 생성 완료")
                
            # 파일 저장 확인
            content_dir = Path(__file__).parent.parent / 'data' / 'topics' / topic / 'content'
            content_file = content_dir / f'{content_type}.json'
            if content_file.exists():
                print(f"- 파일 생성됨: {content_file}")
                print(f"- 파일 크기: {content_file.stat().st_size:,} bytes")
            
        except Exception as e:
            print(f"❌ {topic} 생성 중 오류 발생: {str(e)}")
            print(f"❌ {topic} 생성 실패: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    cli() 