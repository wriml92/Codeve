import os
import sys
import django
from pathlib import Path
import traceback
from datetime import datetime

# Django 설정을 위한 프로젝트 루트 경로 추가
project_root = str(Path(__file__).resolve().parent.parent.parent)
sys.path.append(project_root)

# Django 설정 초기화
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Codeve.settings')
django.setup()

from courses.llm.assignment_llm import AssignmentLLM
import asyncio
import json

# 재생성할 토픽 목록
TOPICS_TO_REGENERATE = [
    'input_output',
    'variables',
    'strings',
    'lists',
    'tuples',
    'loops',
    'conditionals',
    'functions',
    'modules',
    'files',
    'exceptions',
    'dictionaries',
    'classes'
]

async def regenerate_assignment(topic_id):
    print(f"Generating assignments for {topic_id}...")
    try:
        llm = AssignmentLLM()
        
        # content 디렉토리만 사용
        content_dir = llm.data_dir / topic_id / 'content'
        assignment_file = content_dir / 'assignment.json'
        
        print(f"파일 경로:")
        print(f"- 콘텐츠 디렉토리: {content_dir}")
        print(f"- 과제 파일: {assignment_file}")
        
        # content 디렉토리 생성
        content_dir.mkdir(parents=True, exist_ok=True)
        
        # HTML 형식으로 과제 생성
        result = await llm.generate(topic_id)
        
        # 결과 저장
        with open(assignment_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
            
        print(f"✅ 과제 파일 생성 완료: {assignment_file}")
        print(f"- 파일 크기: {assignment_file.stat().st_size:,} bytes")
            
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        traceback.print_exc()

async def main():
    start_time = datetime.now()
    print(f"\n시작 시간: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("과제 재생성을 시작합니다...")
    print(f"대상 토픽: {', '.join(TOPICS_TO_REGENERATE)}\n")
    
    for topic_id in TOPICS_TO_REGENERATE:
        print(f"\n=== {topic_id} 과제 재생성 시작 ===")
        await regenerate_assignment(topic_id)
        print(f"=== {topic_id} 과제 재생성 완료 ===\n")
        # API 호출 제한을 고려하여 잠시 대기
        await asyncio.sleep(2)
    
    end_time = datetime.now()
    duration = end_time - start_time
    
    print("\n모든 과제 재생성이 완료되었습니다!")
    print(f"종료 시간: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"총 소요 시간: {duration.total_seconds():.1f}초")

if __name__ == '__main__':
    asyncio.run(main()) 