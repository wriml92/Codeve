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
import click
import asyncio
import logging
from pathlib import Path
from typing import List

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, project_root)

# Django 설정 초기화
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Codeve.settings')
import django
django.setup()

from courses.llm import ContentGenerator
from courses.llm.theory_llm import TheoryLLM
from courses.llm.practice_llm import PracticeLLM
from courses.llm.assignment_llm import AssignmentLLM
from courses.llm.reflection_llm import ReflectionLLM
from courses.config.constants import TOPICS
import json

# 로깅 설정
def setup_logging():
    """로깅 설정"""
    log_dir = Path(__file__).parent.parent / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    # 로그 포맷 설정
    log_format = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 파일 핸들러 설정 (상세 로그)
    file_handler = logging.FileHandler(
        log_dir / 'cli.log',
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(log_format)
    
    # 콘솔 핸들러 설정 (주요 정보만)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(log_format)
    
    # 로거 설정
    logger = logging.getLogger('codeve')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# 로거 초기화
logger = setup_logging()

# 유효한 토픽 목록
VALID_TOPICS = [topic['id'] for topic in TOPICS]

# 유효한 콘텐츠 타입
VALID_TYPES = ContentGenerator.get_content_types()

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
    logger.info(f"콘텐츠 생성 시작 (type: {type}, topic: {topic}, force: {force})")
    generator = ContentGenerator()
    try:
        if topic:
            asyncio.run(generator.generate_topic(topic, type, force))
        else:
            asyncio.run(generator.generate_all(type, force))
        logger.info("콘텐츠 생성 완료")
    except Exception as e:
        logger.error(f"콘텐츠 생성 중 오류 발생: {str(e)}", exc_info=True)

@cli.command()
@click.option('--topic', help='특정 토픽 ID (옵션)')
def init(topic):
    """과제 템플릿 초기화"""
    logger.info(f"과제 템플릿 초기화 시작 (topic: {topic})")
    try:
        generator = ContentGenerator()
        generator.initialize_templates(topic)
        logger.info("과제 템플릿 초기화 완료")
    except Exception as e:
        logger.error(f"과제 템플릿 초기화 중 오류 발생: {str(e)}", exc_info=True)

@cli.command()
def validate():
    """생성된 콘텐츠 검증"""
    logger.info("콘텐츠 검증 시작")
    try:
        base_dir = Path(__file__).parent.parent
        course_list_path = base_dir / 'data' / 'course_list.json'
        
        with open(course_list_path, 'r', encoding='utf-8') as f:
            course_list = json.load(f)
            logger.debug(f"코스 목록 로드 완료: {len(course_list.get('python', {}).get('topics', []))} 토픽")
        
        generator = ContentGenerator()
        generator.validate_content()
        logger.info("콘텐츠 검증 완료")
    except Exception as e:
        logger.error(f"콘텐츠 검증 중 오류 발생: {str(e)}", exc_info=True)

async def generate_content(content_type: str, topic_id: str = None):
    """콘텐츠 생성"""
    # 콘텐츠 타입 검증
    if content_type not in VALID_TYPES:
        logger.error(f"잘못된 콘텐츠 타입: {content_type}")
        logger.info(f"사용 가능한 타입: {', '.join(VALID_TYPES)}")
        return

    # 토픽 ID 검증
    if topic_id and topic_id not in VALID_TOPICS:
        logger.error(f"잘못된 토픽 ID: {topic_id}")
        logger.info(f"사용 가능한 토픽: {', '.join(VALID_TOPICS)}")
        return

    topics_to_generate = [topic_id] if topic_id else VALID_TOPICS

    for topic in topics_to_generate:
        logger.info(f"=== {topic} 콘텐츠 생성 시작 ===")
        try:
            content = None
            if content_type == 'theory':
                llm = TheoryLLM()
                content = await llm.generate(topic)
                logger.info(f"{topic} 이론 내용 생성 완료")
                
            elif content_type == 'practice':
                llm = PracticeLLM()
                content = await llm.generate(topic)
                logger.info(f"{topic} 실습 내용 생성 완료")
                
            else:  # assignment
                llm = AssignmentLLM()
                result = await llm.generate(topic)
                content = result['content'] if isinstance(result, dict) and 'content' in result else result
                logger.info(f"{topic} 과제 내용 생성 완료")
                
            # 파일 저장 확인
            if content:
                content_dir = Path(__file__).parent.parent / 'data' / 'topics' / topic / 'content'
                content_file = content_dir / f'{content_type}.json'
                if content_file.exists():
                    file_size = content_file.stat().st_size
                    logger.info(f"파일 생성됨: {content_file}")
                    logger.debug(f"파일 크기: {file_size:,} bytes")
            
        except Exception as e:
            logger.error(f"{topic} 생성 중 오류 발생: {str(e)}", exc_info=True)

if __name__ == '__main__':
    cli() 