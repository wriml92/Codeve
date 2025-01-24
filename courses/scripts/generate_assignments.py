"""토픽별 과제 생성 스크립트"""

from pathlib import Path
import json
import asyncio
from langchain_openai import ChatOpenAI
import logging
from datetime import datetime

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_logging():
    """로그 파일 설정"""
    log_dir = Path(__file__).parent / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f'assignment_generation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

async def generate_assignments(topic_id: str, topic_name: str) -> dict:
    """특정 토픽의 과제 생성"""
    llm = ChatOpenAI(model_name="gpt-4", temperature=0.7)
    
    prompt = f"""당신은 Python 교육 전문가입니다. {topic_name} 주제의 과제를 생성해주세요.

다음 형식의 JSON으로 작성해주세요:
{{
    "assignments": [
        {{
            "id": 1,
            "type": "concept",
            "question": "개념 이해를 확인하는 문제",
            "choices": ["보기1", "보기2", "보기3", "보기4"],
            "correct_answer": 정답번호,
            "explanation": "정답 설명",
            "hint": "오답시 힌트"
        }},
        {{
            "id": 2,
            "type": "implementation",
            "question": "실제 구현 문제",
            "constraints": ["제약사항1", "제약사항2"],
            "test_cases": [
                {{"input": "입력값", "output": "기대값"}},
                {{"input": "입력값2", "output": "기대값2"}}
            ],
            "sample_solution": "예시 답안 코드",
            "hints": ["힌트1", "힌트2"]
        }}
    ]
}}

주의사항:
1. 실제 현업에서 마주할 수 있는 상황을 반영해주세요
2. 명확하고 이해하기 쉬운 설명을 제공해주세요
3. 단계적으로 접근할 수 있는 힌트를 제공해주세요
4. 테스트 케이스는 기본/경계/예외 상황을 포함해주세요
5. 반드시 유효한 JSON 형식으로 작성해주세요"""

    try:
        response = await llm.ainvoke(prompt)
        logger.debug(f"Raw response for {topic_id}:\n{response.content}")
        
        # JSON 파싱 시도
        try:
            return json.loads(response.content)
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 오류 ({topic_id}): {str(e)}\n응답 내용:\n{response.content}")
            raise
            
    except Exception as e:
        logger.error(f"과제 생성 중 오류 발생 ({topic_id}): {str(e)}")
        raise

async def main():
    setup_logging()
    logger.info("과제 생성 시작")
    
    # 진행 상황 파일 경로
    progress_file = Path(__file__).parent / 'generation_progress.json'
    
    # 이전 진행 상황 로드
    completed_topics = set()
    if progress_file.exists():
        with open(progress_file, 'r', encoding='utf-8') as f:
            completed_topics = set(json.load(f))
    
    # course_list.json에서 토픽 목록 로드
    course_list_path = Path(__file__).parent.parent / 'data' / 'course_list.json'
    with open(course_list_path, 'r', encoding='utf-8') as f:
        topics = json.load(f)['python']['topics']
    
    for topic in topics:
        if topic['id'] in completed_topics:
            logger.info(f"Skipping {topic['name']} (already completed)")
            continue
            
        try:
            logger.info(f"Generating assignments for {topic['name']}...")
            
            # 과제 생성
            assignments = await generate_assignments(
                topic_id=topic['id'],
                topic_name=topic['name']
            )
            
            # 과제 저장
            output_dir = Path(__file__).parent.parent / 'data' / 'topics' / topic['id'] / 'content'
            output_dir.mkdir(parents=True, exist_ok=True)
            
            with open(output_dir / 'assignment.json', 'w', encoding='utf-8') as f:
                json.dump(assignments, f, ensure_ascii=False, indent=2)
            
            # 진행 상황 업데이트
            completed_topics.add(topic['id'])
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(list(completed_topics), f)
                
            logger.info(f"✓ Generated {len(assignments['assignments'])} assignments for {topic['name']}")
            print(f"✓ Generated {len(assignments['assignments'])} assignments for {topic['name']}")
            
        except Exception as e:
            logger.error(f"Failed to generate assignments for {topic['name']}: {str(e)}")
            print(f"❌ Failed to generate assignments for {topic['name']}")
            continue

if __name__ == '__main__':
    asyncio.run(main()) 