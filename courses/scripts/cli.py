import os
import django

# Django 설정 초기화
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Codeve.settings')
django.setup()

import click
from pathlib import Path
import asyncio
from typing import List
from courses.llm import ContentGenerator  # ContentGenerator로 통합
from courses.llm.theory_llm import TheoryLLM
from courses.llm.practice_llm import PracticeLLM
from courses.llm.assignment_llm import AssignmentLLM
from courses.llm.reflection_llm import ReflectionLLM
import json
from courses.config.constants import TOPICS  # views.py 대신 config/constants.py에서 import

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
            elif content_type == 'practice':
                llm = PracticeLLM()
            else:  # assignment
                llm = AssignmentLLM()
            
            await llm.generate(topic)
            print(f"✅ {topic} 생성 완료")
        except Exception as e:
            print(f"❌ {topic} 생성 중 오류 발생: {str(e)}")
            print(f"❌ {topic} 생성 실패: {str(e)}")

if __name__ == '__main__':
    cli() 