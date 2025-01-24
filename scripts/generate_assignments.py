"""
자동 과제 생성 스크립트

이 스크립트는 Python 교육 플랫폼의 과제를 자동으로 생성합니다.
GPT-4를 활용하여 각 토픽별로 다양한 유형의 과제를 생성하고 JSON 형식으로 저장합니다.

생성되는 과제 유형:
1. 이론 개념 문제 (Theory Concept)
   - Python 개념에 대한 이해를 테스트하는 객관식 문제
   - 예: input() 함수의 기본 동작 이해

2. 비유 문제 (Metaphor)
   - 프로그래밍 개념을 실생활에 비유한 객관식 문제
   - 예: 콘솔 입출력을 대화에 비유

3. 실제 개념 문제 (Practical Concept)
   - 실제 코드 사용과 관련된 객관식 문제
   - 예: 변수에 입력값 저장하는 방법

4. 분석 문제 (Analysis)
   - 주어진 코드를 분석하고 설명하는 문제
   - 예: 간단한 입출력 프로그램 분석

5. 구현 문제 (Implementation)
   - 실제 코드를 작성하는 문제
   - 예: 두 숫자를 입력받아 합 계산하기

저장 위치:
- 기본 경로: courses/data/topics/{topic_id}/content/
- 파일명: assignment.json

사용 방법:
1. 전체 토픽 과제 생성:
   python generate_assignments.py

2. 특정 토픽 과제 생성:
   python generate_assignments.py input_output

주의사항:
- OpenAI API 키가 환경변수에 설정되어 있어야 함
- 과제 생성에는 토픽당 약 1-2분 소요
- 이미 존재하는 과제는 덮어쓰기됨
"""

import json
import asyncio
from pathlib import Path
from langchain_community.chat_models import ChatOpenAI
from typing import Dict

# TOPICS 리스트 정의
TOPICS = [
    {'id': 'input_output', 'name': '입출력'},
    {'id': 'variables', 'name': '변수'},
    {'id': 'strings', 'name': '문자열'},
    {'id': 'lists', 'name': '리스트'},
    {'id': 'tuples', 'name': '튜플'},
    {'id': 'dictionaries', 'name': '딕셔너리'},
    {'id': 'conditionals', 'name': '조건문'},
    {'id': 'loops', 'name': '반복문'},
    {'id': 'functions', 'name': '함수'},
    {'id': 'classes', 'name': '클래스'},
    {'id': 'modules', 'name': '모듈'},
    {'id': 'exceptions', 'name': '예외처리'},
    {'id': 'files', 'name': '파일 입출력'}
]

async def generate_assignments(topic_id: str, topic_name: str) -> Dict:
    """토픽별 과제 생성"""
    json_template = '''
    {
        "assignments": [
            {
                "id": 1,
                "type": "theory_concept",
                "question": "이론적 개념에 대한 문제 내용",
                "choices": ["선택지1", "선택지2", "선택지3", "선택지4"],
                "correct_answer": 1,
                "explanation": "정답 설명",
                "hint": "힌트"
            },
            {
                "id": 2,
                "type": "metaphor",
                "question": "실생활 비유를 통한 문제 내용",
                "choices": ["선택지1", "선택지2", "선택지3", "선택지4"],
                "correct_answer": 1,
                "explanation": "정답 설명",
                "hint": "힌트"
            },
            {
                "id": 3,
                "type": "concept",
                "question": "실제 코드 관련 문제 내용",
                "choices": ["선택지1", "선택지2", "선택지3", "선택지4"],
                "correct_answer": 1,
                "explanation": "정답 설명",
                "hint": "힌트"
            },
            {
                "id": 4,
                "type": "analysis",
                "question": "분석할 코드와 함께 문제 내용",
                "code_to_analyze": "분석할 파이썬 코드",
                "points_to_consider": ["고려할 점1", "고려할 점2"],
                "sample_analysis": "모범 분석 예시"
            },
            {
                "id": 5,
                "type": "implementation",
                "question": "구현 문제 내용",
                "constraints": ["제약사항1", "제약사항2"],
                "test_cases": [
                    {"input": "테스트 입력1", "output": "기대 출력1"},
                    {"input": "테스트 입력2", "output": "기대 출력2"}
                ],
                "sample_solution": "예시 답안 코드",
                "hints": ["힌트1", "힌트2"]
            }
        ]
    }
    '''

    prompt = f"""Generate 5 Python programming assignments for the topic '{topic_name}' ({topic_id}).

IMPORTANT: For the 'input_output' topic, focus ONLY on Python's input() and print() functions for console input/output. 
DO NOT include ANY file input/output or file handling concepts. The assignments should only cover:
- How to use input() to get user input from console
- How to use print() to display output to console
- Basic string formatting with print()
- Common patterns with console input/output

The assignments should include:
1. Theory concept question about input()/print() usage
2. Metaphor/analogy question comparing console I/O to real-world scenarios
3. Practical concept question about input()/print() behavior
4. Code analysis question examining a simple program using input()/print()
5. Implementation task requiring use of input()/print()

For all other topics, generate normal programming assignments covering:
{json_template}
"""

    llm = ChatOpenAI(
        model="gpt-4-0125-preview",
        temperature=0.7,
        max_tokens=2000
    )

    try:
        response = await llm.ainvoke(prompt)
        content = response.content if hasattr(response, 'content') else str(response)
        print(f"Raw response content: {content}")  # 디버깅용
        
        # ```json 태그 제거
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0].strip()
        
        return json.loads(content)
    except Exception as e:
        print(f"Error generating assignments for {topic_id}: {str(e)}")
        return None

async def save_assignments(topic_id: str, assignments: dict) -> None:
    """과제 데이터를 파일로 저장"""
    try:
        # 파일 경로 설정
        base_dir = Path(__file__).parent.parent / 'courses' / 'data' / 'topics' / topic_id / 'content'
        base_dir.mkdir(parents=True, exist_ok=True)
        
        assignment_file = base_dir / 'assignment.json'
        
        # 데이터 저장
        with open(assignment_file, 'w', encoding='utf-8') as f:
            json.dump(assignments, f, ensure_ascii=False, indent=2)
            
        print(f"Successfully saved assignments for {topic_id}")
    except Exception as e:
        print(f"Error saving assignments for {topic_id}: {str(e)}")

async def main():
    """메인 함수"""
    for topic in TOPICS:
        print(f"\nGenerating assignments for {topic['name']} ({topic['id']})...")
        assignments = await generate_assignments(topic['id'], topic['name'])
        if assignments:
            await save_assignments(topic['id'], assignments)
        else:
            print(f"Failed to generate assignments for {topic['id']}")

if __name__ == "__main__":
    asyncio.run(main()) 