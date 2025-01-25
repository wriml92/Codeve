"""
과제 생성을 위한 LLM(Language Learning Model) 클래스

이 모듈은 토픽별 과제를 자동으로 생성하는 기능을 제공합니다.
GPT를 활용하여 이론과 실습 내용을 바탕으로 다양한 유형의 과제를 생성합니다.

주요 기능:
1. 과제 유형별 자동 생성
   - concept: 기본 개념 이해를 테스트하는 객관식 문제
   - theory_concept: 이론 개념을 실생활에 연결하는 객관식 문제
   - metaphor: 프로그래밍 개념을 비유로 설명하는 객관식 문제
   - implementation_basic: 기초적인 코드 구현 문제

2. 과제 데이터 생성
   - HTML 형식의 과제 문제 생성 (assignments/ui/assignment.html)
   - JSON 형식의 정답 데이터 생성 (assignments/answers/assignment_answers.json)

3. 자동화된 기능
   - 문제와 보기 자동 생성
   - 테스트 케이스 자동 생성
   - 힌트와 피드백 자동 생성

사용 예시:
    llm = AssignmentLLM()
    result = await llm.generate('input_output')  # input_output 토픽의 과제 생성
"""
from typing import Dict, Any, List
from .base_llm import BaseLLM
import json
from pathlib import Path
from datetime import datetime
from langchain_community.chat_models import ChatOpenAI
import asyncio
import os
from dotenv import load_dotenv

class AssignmentLLM(BaseLLM):
    """
    과제 생성을 위한 LLM 클래스
    이론과 실습 내용을 바탕으로 다양한 유형의 과제를 자동으로 생성합니다.
    """
    
    def __init__(self, api_key):
        """
        AssignmentLLM 초기화
        과제 유형 목록과 기본 디렉토리, 프롬프트 템플릿을 설정합니다.
        """
        super().__init__()
        self.llm = ChatOpenAI(
            model_name="gpt-4-1106-preview",
            temperature=0.7,
            openai_api_key=api_key
        )
        self.base_dir = Path(__file__).parent.parent
        self.data_dir = self.base_dir / 'data' / 'topics'
        
        # 과제 유형과 ID 매핑
        self.assignment_type_ids = {
            'concept_basic': 1, # 객관식 1: 기본 개념 이해 (핵심 정의와 용어)
            'concept_application': 2,# 객관식 2: 개념 적용 (주어진 상황에서 개념 적용)
            'concept_analysis': 3, # 객관식 3: 코드 분석 (주어진 코드의 결과나 동작 예측)
            'concept_debug': 4, # 객관식 4: 디버깅 (잘못된 코드나 상황에서 문제 찾기)
            'metaphor': 5, # 객관식 5: 비유 (프로그래밍 개념을 비유로 설명)
            'theory_concept': 6, # 객관식 6: 이론 개념 (이론 내용을 실생활에 연결)
            'concept_synthesis': 7, # 객관식 7: 개념 통합 (여러 개념을 연결하여 문제 해결)
            'implementation_playground': 8, # 구현 1: 주어진 코드 실행해보고 결과 관찰하기
            'implementation_modify': 9, # # 구현 2: 주어진 코드 일부 수정하기
            'implementation_creative': 10 # 구현 3: 재미있는 상황 속 간단한 코드 작성 (변수명과 상세 힌트 제공)
        }
        
        # 과제 유형 정의
        self.assignment_types = list(self.assignment_type_ids.keys())
        self.prompt_template = self.load_prompt('assignment_llm_prompt.md')
        
    def _get_current_timestamp(self) -> str:
        """
        현재 시간을 ISO 형식으로 반환
        
        Returns:
            str: ISO 형식의 현재 시간
        """
        return datetime.now().isoformat()
        
    def _get_topic_name(self, topic_id: str) -> str:
        """
        토픽 ID에 해당하는 토픽 이름을 course_list.json에서 가져옴
        
        Args:
            topic_id (str): 토픽 ID
            
        Returns:
            str: 토픽 이름 또는 토픽 ID (이름을 찾지 못한 경우)
        """
        try:
            with open(self.base_dir / 'data' / 'course_list.json', 'r', encoding='utf-8') as f:
                course_data = json.load(f)
                for topic in course_data.get('topics', []):
                    if topic.get('id') == topic_id:
                        return topic.get('name', topic_id)
            return topic_id
        except (FileNotFoundError, json.JSONDecodeError):
            return topic_id
        
    async def generate(self, topic_id: str) -> Dict[str, Any]:
        """
        토픽별 과제 HTML과 정답 데이터 생성
        
        Args:
            topic_id (str): 과제를 생성할 토픽의 ID
            
        Returns:
            Dict[str, Any]: 생성된 과제 HTML과 정답 데이터를 포함하는 딕셔너리
            {
                'content': HTML 형식의 과제 내용,
                'metadata': 정답 데이터와 메타데이터
            }
        """
        # 이론과 실습 내용 참조
        theory_file = self.data_dir / topic_id / 'content' / 'theory' / 'theory.html'
        practice_file = self.data_dir / topic_id / 'content' / 'practice' / 'practice.json'
        
        theory_content = ""
        practice_content = ""
        
        if theory_file.exists():
            with open(theory_file, 'r', encoding='utf-8') as f:
                theory_content = f.read()
        
        if practice_file.exists():
            with open(practice_file, 'r', encoding='utf-8') as f:
                practice_data = json.load(f)
                practice_content = practice_data.get('content', '')
                
        # 토픽 정보 로드
        topic_name = self._get_topic_name(topic_id)
        
        # 과제 데이터 생성
        assignments = []  # 정답 데이터용
        problem_data = []  # 문제 데이터용
        html_content = """<div class="space-y-8">"""
        
        # 기존 과제 데이터 로드 (특정 유형만 생성할 때 필요)
        existing_assignments = {}
        assignments_file = self.data_dir / topic_id / 'content' / 'assignments' / 'data' / 'assignment.json'
        if assignments_file.exists():
            with open(assignments_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for assignment in data.get('assignments', []):
                    existing_assignments[assignment['type']] = assignment
        
        for type_ in self.assignment_types:
            # 과제 ID 설정
            assignment_id = self.assignment_type_ids[type_]
            
            # 시스템 프롬프트에 이론과 실습 내용 포함
            system_prompt = f"""당신은 Python 과제 생성 튜터입니다.
현재 다루는 주제: {topic_name}

이론 내용:
{theory_content}

실습 내용:
{practice_content}

다음 규칙을 반드시 따라주세요:
1. 이론 내용에서 다룬 핵심 개념을 테스트하는 문제를 출제하세요
2. 실습에서 연습한 내용을 응용할 수 있는 문제를 만드세요
3. 문제의 난이도는 실습보다 약간 높되, 학습한 내용으로 해결 가능해야 합니다
4. 비전공자도 이해할 수 있도록 쉽고 명확한 언어를 사용하세요
5. 힌트는 이론과 실습 내용을 참고하여 구체적으로 제시하세요"""

            prompt = self._get_assignment_prompt(topic_name, type_)
            
            # GPT 호출
            response = await self.generate_completion(prompt)
            assignment_data = self._parse_assignment_response(response, type_)
            
            # ID 설정
            assignment_data['id'] = assignment_id
            assignment_data['type'] = type_
            
            problem_data.append(assignment_data)  # 문제 데이터 저장
            
            # 정답 데이터 저장
            answer_data = {
                'id': assignment_id,
                'type': type_
            }
            
            if type_ in ['concept_basic', 'concept_application', 'concept_analysis', 
                        'concept_debug', 'metaphor', 'theory_concept', 'concept_synthesis']:
                # 객관식 문제 HTML 생성
                html_content += f"""
                <div class="bg-white rounded-lg p-6 shadow-md">
                    <h3 class="text-lg font-semibold mb-4">{assignment_data['content']}</h3>
                    <form class="space-y-4">
                        {''.join([
                            f'''<div class="flex items-center space-x-2 my-2">
                                <input type="radio" name="assignment{assignment_id}_answer" value="{i+1}" class="form-radio">
                                <label>{choice}</label>
                            </div>'''
                            for i, choice in enumerate(assignment_data['choices'])
                        ])}
                    </form>
                    <button onclick="submitAssignment({assignment_id}, '{type_}')"
                        class="mt-6 w-full px-6 py-3 bg-gradient-to-r from-amber-500 to-yellow-400 text-white font-semibold rounded-xl shadow-md hover:shadow-lg transform hover:-translate-y-0.5 transition-all duration-200 hover:from-amber-600 hover:to-yellow-500 flex items-center justify-center">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                        </svg>
                        문제 제출하기
                    </button>
                    <div id="result{assignment_id}" class="mt-4 hidden">
                        <div class="p-4 rounded-lg"></div>
                    </div>
                </div>"""
                
                answer_data.update({
                    'correct_answer': assignment_data['correct_answer'],
                    'hint': assignment_data['hint']
                })
                
            else:
                # 구현 문제 HTML 생성
                html_content += f"""
                <div class="bg-white rounded-lg p-6 shadow-md">
                    <h3 class="text-lg font-semibold mb-4">{assignment_data['content']}</h3>
                    <div class="space-y-4">
                        <div class="bg-gray-50 p-4 rounded">
                            <h4 class="font-medium mb-2">테스트 케이스:</h4>
                            {''.join([
                                f'''<div class="my-2">
                                    <p class="text-sm text-gray-600">입력: {tc['input']}</p>
                                    <p class="text-sm text-gray-600">출력: {tc['output']}</p>
                                </div>'''
                                for tc in assignment_data['test_cases']
                            ])}
                        </div>
                        <div class="mt-4">
                            <div id="editor{assignment_id}" class="code-editor h-32 border rounded"></div>
                        </div>
                        <button onclick="submitAssignment({assignment_id}, '{type_}')"
                            class="mt-6 w-full px-6 py-3 bg-gradient-to-r from-amber-500 to-yellow-400 text-white font-semibold rounded-xl shadow-md hover:shadow-lg transform hover:-translate-y-0.5 transition-all duration-200 hover:from-amber-600 hover:to-yellow-500 flex items-center justify-center">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                            </svg>
                            코드 제출하기
                        </button>
                        <div id="result{assignment_id}" class="mt-4 hidden">
                            <div class="p-4 rounded-lg"></div>
                        </div>
                    </div>
                </div>"""
                
                answer_data.update({
                    'test_cases': assignment_data['test_cases'],
                    'hint': assignment_data['hint']
                })
            
            assignments.append(answer_data)
        
        html_content += "</div>"
        
        # HTML 파일 저장
        content_dir = self.data_dir / topic_id / 'content'
        assignments_dir = content_dir / 'assignments'
        assignments_dir.mkdir(parents=True, exist_ok=True)
        
        with open(assignments_dir / 'ui' / 'assignment.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        # 정답 데이터 저장
        answer_data = {
            'assignments': assignments,
            'metadata': {
                'version': 1,
                'created_at': self._get_current_timestamp()
            }
        }
        
        with open(assignments_dir / 'answers' / 'assignment_answers.json', 'w', encoding='utf-8') as f:
            json.dump(answer_data, f, indent=2, ensure_ascii=False)
            
        # assignment.json 파일도 생성 (문제와 보기만 포함)
        assignment_data = {
            'assignments': [
                {
                    'id': idx,
                    'type': type_,
                    'content': problem['content'],
                    'choices': problem['choices'] if type_ in ['concept_basic', 'concept_application', 
                                                                 'concept_analysis', 'concept_debug', 
                                                                 'metaphor', 'theory_concept', 
                                                                 'concept_synthesis'] else None,
                    'test_cases': problem['test_cases'] if type_ in ['implementation_playground', 
                                                                   'implementation_modify',
                                                                   'implementation_creative'] else None,
                    'constraints': problem.get('constraints')
                }
                for idx, (type_, problem) in enumerate(zip(self.assignment_types, problem_data), 1)
            ],
            'metadata': {
                'version': 1,
                'created_at': self._get_current_timestamp()
            }
        }
        
        with open(assignments_dir / 'data' / 'assignment.json', 'w', encoding='utf-8') as f:
            json.dump(assignment_data, f, indent=2, ensure_ascii=False)
            
        return {
            'content': html_content,
            'metadata': answer_data['metadata']
        }

    def _get_assignment_prompt(self, topic_name: str, assignment_type: str) -> str:
        """
        과제 생성을 위한 프롬프트 반환
        
        Args:
            topic_name (str): 토픽 이름
            assignment_type (str): 과제 유형 ('concept', 'theory_concept', 'metaphor', 'implementation_basic')
            
        Returns:
            str: 과제 생성을 위한 GPT 프롬프트
        """
        prompts = {
            'concept_basic': f"""
                {topic_name}의 가장 핵심적인 정의나 용어를 묻는 객관식 문제를 생성해주세요.
                비전공자가 처음 프로그래밍을 배우는 상황임을 고려하여, 매우 쉽고 명확한 문제를 만들어주세요.
                이론 수업에서 처음 배운 핵심 개념을 확인하는 문제여야 합니다.
                
                다음 규칙을 반드시 따라주세요:
                1. 문제는 한 문장으로 간단하게 작성해주세요
                2. "~는 무엇인가요?" 또는 "~의 정의는?" 형태로 작성하세요
                3. 보기는 명확하게 구분되도록 작성하세요
                4. 오답도 해당 주제와 관련된 내용으로 구성하세요
                5. 힌트는 이론에서 설명한 정의를 간단히 상기시켜주세요

                다음 형식으로 반환해주세요:
                {{
                    "content": "문제 내용",
                    "choices": ["보기1", "보기2", "보기3", "보기4"],
                    "correct_answer": "정답 번호(1-4)",
                    "hint": "힌트 내용"
                }}
            """,
            'concept_application': f"""
                {topic_name}의 개념을 실제 상황에 적용하는 객관식 문제를 생성해주세요.
                비전공자가 처음 프로그래밍을 배우는 상황임을 고려하여, 매우 쉽고 명확한 문제를 만들어주세요.
                
                다음 규칙을 반드시 따라주세요:
                1. 문제는 실제 코드를 작성할 때 마주치는 상황을 제시하세요
                2. 하나의 짧은 시나리오를 제시하고 "어떻게 해야 할까요?" 형태로 질문하세요
                3. 보기는 실제 코드 작성 시 선택할 수 있는 구체적인 방법들로 구성하세요
                4. 모든 보기는 문법적으로는 맞지만, 상황에 가장 적절한 것을 고르게 하세요
                5. 힌트는 이론에서 배운 내용과 실제 적용을 연결해주세요

                예시 형태:
                "파이썬에서 사용자의 나이를 저장하려고 합니다. 어떤 방법이 가장 적절할까요?"
                
                다음 형식으로 반환해주세요:
                {{
                    "content": "문제 내용",
                    "choices": ["보기1", "보기2", "보기3", "보기4"],
                    "correct_answer": "정답 번호(1-4)",
                    "hint": "힌트 내용"
                }}
            """,
            'concept_analysis': f"""
                {topic_name}에 대한 코드 분석 문제를 생성해주세요.
                비전공자가 처음 프로그래밍을 배우는 상황임을 고려하여, 매우 쉽고 명확한 문제를 만들어주세요.
                
                다음 규칙을 반드시 따라주세요:
                1. 2-3줄의 매우 간단한 코드를 제시하세요
                2. 코드의 실행 결과나 동작을 예측하는 문제를 만드세요
                3. 보기는 실제 실행 결과와 비슷하지만 틀린 것들로 구성하세요
                4. 코드는 <code> 태그로 감싸서 제시하세요
                
                예시 형태:
                "다음 코드를 실행하면 어떤 결과가 출력될까요?<br><br><code>x = 5<br>y = x + 3<br>print(y)</code>"
                
                다음 형식으로 반환해주세요:
                {{
                    "content": "문제 내용",
                    "choices": ["보기1", "보기2", "보기3", "보기4"],
                    "correct_answer": "정답 번호(1-4)",
                    "hint": "힌트 내용"
                }}
            """,
            'concept_debug': f"""
                {topic_name}에 대한 디버깅 문제를 생성해주세요.
                비전공자가 처음 프로그래밍을 배우는 상황임을 고려하여, 매우 쉽고 명확한 문제를 만들어주세요.
                
                다음 규칙을 반드시 따라주세요:
                1. 2-3줄의 매우 간단한 코드에 하나의 오류만 포함하세요
                2. 오류는 이론에서 배운 내용과 관련된 것이어야 합니다
                3. 보기는 발생할 수 있는 오류들로 구성하되, 확실히 구분되게 작성하세요
                4. 코드는 <code> 태그로 감싸서 제시하세요
                5. 힌트는 오류가 발생하는 상황과 원인을 이해하기 쉽게 설명하세요
                
                예시 형태:
                "다음 코드에서 발생하는 오류는 무엇일까요?<br><br><code>age = input('나이: ')<br>result = age + 5<br>print(result)</code>"
                
                다음 형식으로 반환해주세요:
                {{
                    "content": "문제 내용",
                    "choices": ["보기1", "보기2", "보기3", "보기4"],
                    "correct_answer": "정답 번호(1-4)",
                    "hint": "힌트 내용"
                }}
            """,
            'metaphor': f"""
                {topic_name}을 설명할 때 사용한 비유나 예시를 테스트하는 객관식 문제를 생성해주세요.
                프로그래밍 개념을 일상생활의 친숙한 상황에 비유하여 설명하는 문제를 만들어주세요.
                비전공자도 직관적으로 이해할 수 있는 쉬운 비유를 사용해주세요.
                문제는 한 문장으로 명확하게 질문해주세요.
                보기는 구체적인 일상생활 예시로 작성해주세요.
                다음 형식으로 반환해주세요:
                {{
                    "content": "문제 내용",
                    "choices": ["보기1", "보기2", "보기3", "보기4"],
                    "correct_answer": "정답 번호(1-4)",
                    "hint": "힌트 내용"
                }}
            """,
            'theory_concept': f"""
                {topic_name}의 개념을 실생활 상황과 연결하는 객관식 문제를 생성해주세요.
                비전공자가 처음 프로그래밍을 배우는 상황임을 고려하여, 매우 쉽고 명확한 문제를 만들어주세요.
                
                다음 규칙을 반드시 따라주세요:
                1. 실생활에서 흔히 겪을 수 있는 상황을 예시로 사용하세요 (예: 쇼핑, 요리, 학교생활 등)
                2. 문제는 다음 3단계로 구성하세요:
                   - 실생활 상황 설명 (1-2문장)
                   - 관련된 파이썬 코드 (2-3줄)
                   - "이 코드의 결과는 실생활에서 무엇과 같을까요?" 형태의 질문
                3. 코드는 <code> 태그로 감싸고, 줄바꿈은 <br> 태그를 사용하세요
                4. 보기는 실생활의 구체적인 상황이나 결과로 작성하세요
                5. 힌트는 코드와 실생활 상황의 연결점을 설명하세요
                
                예시 형태:
                "마트에서 장보기를 할 때 각 물건의 가격을 계산하는 상황을 생각해봅시다.<br><br><code>apple = 1000<br>count = 3<br>total = apple * count</code><br><br>위 코드는 실생활의 어떤 상황과 가장 비슷할까요?"
                
                다음 형식으로 반환해주세요:
                {{
                    "content": "문제 내용",
                    "choices": ["보기1", "보기2", "보기3", "보기4"],
                    "correct_answer": "정답 번호(1-4)",
                    "hint": "힌트 내용"
                }}
            """,
            'concept_synthesis': f"""
                {topic_name}의 개념들을 연결하여 해결하는 객관식 문제를 생성해주세요.
                비전공자가 처음 프로그래밍을 배우는 상황임을 고려하여, 매우 쉽고 명확한 문제를 만들어주세요.
                
                다음 규칙을 반드시 따라주세요:
                1. 이론에서 배운 2-3개의 개념을 자연스럽게 연결하는 상황을 제시하세요
                2. 문제는 다음 구조로 작성하세요:
                   - 상황 설명 (1-2문장)
                   - 간단한 코드 예시 (2-3줄)
                   - "이 코드에서 사용된 개념들의 올바른 설명은?" 형태의 질문
                3. 코드는 <code> 태그로 감싸고, 줄바꿈은 <br> 태그를 사용하세요
                4. 보기는 여러 개념의 관계를 설명하는 문장으로 작성하세요
                5. 힌트는 각 개념의 역할과 연결성을 설명하세요
                
                예시 형태:
                "다음 코드는 여러 개의 숫자를 처리합니다.<br><br><code>numbers = [1, 2, 3]<br>total = sum(numbers)<br>print(total)</code><br><br>위 코드에서 사용된 개념들의 올바른 설명은 무엇일까요?"
                
                다음 형식으로 반환해주세요:
                {{
                    "content": "문제 내용",
                    "choices": ["보기1", "보기2", "보기3", "보기4"],
                    "correct_answer": "정답 번호(1-4)",
                    "hint": "힌트 내용"
                }}
            """,
            'implementation_playground': f"""
                {topic_name}에 대한 코드 실행/관찰 문제를 생성해주세요.
                비전공자가 처음 프로그래밍을 배우는 상황임을 고려하여, 매우 쉽고 명확한 문제를 만들어주세요.
                
                다음 규칙을 반드시 따라주세요:
                1. 이미 작성된 코드를 제공하고 실행해보게 하세요
                2. 코드를 조금씩 수정하면서 결과가 어떻게 바뀌는지 관찰하게 하세요
                3. 단순 입력/출력 문제는 피하고, 코드셀과 친숙해질 수 있는 내용으로 구성하세요
                4. 모든 변수명과 함수는 이미 정의되어 있어야 합니다
                5. 힌트는 코드의 각 부분이 어떤 역할을 하는지 설명해주세요
                
                예시 형태:
                "다음 코드를 실행해보고, 숫자를 바꿔가며 그려지는 도형이 어떻게 변하는지 관찰해보세요."
                
                다음 형식으로 반환해주세요:
                {{
                    "content": "문제 내용",
                    "test_cases": [
                        {{"input": "제공된 코드", "output": "예상 결과"}},
                        {{"input": "수정된 코드", "output": "예상 결과"}}
                    ],
                    "hint": "힌트 내용"
                }}
            """,
            'implementation_modify': f"""
                {topic_name}에 대한 코드 수정 문제를 생성해주세요.
                비전공자가 처음 프로그래밍을 배우는 상황임을 고려하여, 매우 쉽고 명확한 문제를 만들어주세요.
                
                다음 규칙을 반드시 따라주세요:
                1. 거의 완성된 코드를 제공하고 빈 부분만 채우게 하세요
                2. 빈 부분은 최대 1-2줄로 제한하세요
                3. 단순 입력/출력 문제는 피하고, 코드셀과 친숙해질 수 있는 내용으로 구성하세요
                4. 모든 변수명과 함수는 미리 정의해주세요
                5. 힌트는 빈 부분에 들어갈 내용의 형태나 예시를 구체적으로 제시하세요
                
                예시 형태:
                "다음 코드의 빈 부분을 채워 웃는 이모티콘을 완성해보세요."
                
                다음 형식으로 반환해주세요:
                {{
                    "content": "문제 내용",
                    "test_cases": [
                        {{"input": "제공된 코드", "output": "예상 결과"}},
                        {{"input": "다른 예시", "output": "예상 결과"}}
                    ],
                    "hint": "힌트 내용"
                }}
            """,
            'implementation_creative': f"""
                {topic_name}에 대한 창의적 코드 작성 문제를 생성해주세요.
                비전공자가 처음 프로그래밍을 배우는 상황임을 고려하여, 매우 쉽고 명확한 문제를 만들어주세요.
                
                다음 규칙을 반드시 따라주세요:
                1. 게임, 예술, 일상생활 등 재미있는 상황 속에서 코드를 작성하게 하세요
                2. 코드는 최대 3-4줄로 제한하세요
                3. 단순 입력/출력 문제는 피하고, 코드셀과 친숙해질 수 있는 내용으로 구성하세요
                4. 필요한 모든 변수명과 함수를 미리 정의해주세요
                5. 힌트는 다음을 포함하세요:
                   - 사용할 수 있는 변수/함수 목록
                   - 각 변수/함수의 역할
                   - 코드 작성 순서 가이드
                
                예시 형태:
                "주어진 함수들을 사용해서 나만의 캐릭터를 그려보세요."
                
                다음 형식으로 반환해주세요:
                {{
                    "content": "문제 내용",
                    "test_cases": [
                        {{"input": "예시 코드", "output": "예상 결과"}},
                        {{"input": "다른 예시", "output": "예상 결과"}}
                    ],
                    "hint": "힌트 내용"
                }}
            """
        }
        return prompts[assignment_type]

    def _parse_assignment_response(self, response: str, assignment_type: str) -> Dict[str, Any]:
        """LLM 응답을 파싱하여 과제 데이터로 변환"""
        try:
            # 응답 로깅
            print(f"\n응답 파싱 시도 ({assignment_type}):")
            print(response)
            
            # JSON 파싱
            data = json.loads(response)
            
            # 필수 필드 확인
            required_fields = {
                'concept_basic': ['content', 'choices', 'correct_answer', 'hint'],
                'concept_application': ['content', 'choices', 'correct_answer', 'hint'],
                'concept_analysis': ['content', 'choices', 'correct_answer', 'hint'],
                'concept_debug': ['content', 'choices', 'correct_answer', 'hint'],
                'metaphor': ['content', 'choices', 'correct_answer', 'hint'],
                'theory_concept': ['content', 'choices', 'correct_answer', 'hint'],
                'concept_synthesis': ['content', 'choices', 'correct_answer', 'hint'],
                'implementation_playground': ['content', 'test_cases', 'hint'],
                'implementation_modify': ['content', 'test_cases', 'hint'],
                'implementation_creative': ['content', 'test_cases', 'hint']
            }
            
            # 필수 필드가 있는지 확인
            if assignment_type in required_fields:
                missing_fields = [field for field in required_fields[assignment_type] if field not in data]
                if missing_fields:
                    print(f"누락된 필드: {missing_fields}")
                    return self._get_default_assignment(assignment_type)
            
            return data
            
        except json.JSONDecodeError as e:
            print(f"JSON 파싱 오류: {str(e)}")
            return self._get_default_assignment(assignment_type)
        except Exception as e:
            print(f"기타 오류: {str(e)}")
            return self._get_default_assignment(assignment_type)
    
    def _get_default_assignment(self, assignment_type: str) -> Dict[str, Any]:
        """기본 과제 템플릿 반환"""
        if assignment_type in ['concept_basic', 'concept_application', 'concept_analysis', 
                             'concept_debug', 'metaphor', 'theory_concept', 'concept_synthesis']:
            return {
                'content': '문제를 준비 중입니다.',
                'choices': ['준비 중'] * 4,
                'correct_answer': '1',
                'hint': '준비 중입니다.'
            }
        else:
            return {
                'content': '문제를 준비 중입니다.',
                'test_cases': [{'input': '', 'output': ''}],
                'hint': '준비 중입니다.'
            }

    async def analyze(self, submission: str) -> Dict[str, Any]:
        """과제 제출물 분석"""
        return {
            'code_quality': 'good',
            'test_results': [],
            'feedback': '잘 작성되었습니다.'
        } 