from typing import Dict, Any, List
from .base_llm import BaseLLM
import json
from pathlib import Path
from datetime import datetime

class AssignmentLLM(BaseLLM):
    def __init__(self):
        super().__init__()
        self.assignment_types = [
            'concept',          # 기본 개념 이해
            'theory_concept',   # 이론 개념 문제
            'metaphor',         # 비유 문제
            'implementation_basic',    # 기본 구현 문제 1
            'implementation_basic'     # 기본 구현 문제 2
        ]
        self.data_dir = self.base_dir / 'data' / 'topics'
        self.prompt_template = self.load_prompt('assignment_llm_prompt.md')
        
    def _get_current_timestamp(self) -> str:
        """현재 시간을 ISO 형식으로 반환"""
        return datetime.now().isoformat()
        
    def _get_topic_name(self, topic_id: str) -> str:
        """토픽 ID에 해당하는 토픽 이름을 course_list.json에서 가져옴"""
        try:
            with open(self.base_dir / 'data' / 'course_list.json', 'r', encoding='utf-8') as f:
                course_data = json.load(f)
                # course_data에서 topic_id에 해당하는 이름 찾기
                for topic in course_data.get('topics', []):
                    if topic.get('id') == topic_id:
                        return topic.get('name', topic_id)
            return topic_id
        except (FileNotFoundError, json.JSONDecodeError):
            return topic_id
        
    async def generate_assignment(self, topic_id: str) -> Dict[str, Any]:
        """토픽별 과제 생성"""
        # 토픽 정보 로드
        topic_name = self._get_topic_name(topic_id)
        
        assignments = []
        for idx, type_ in enumerate(self.assignment_types, 1):
            prompt = self._get_assignment_prompt(topic_name, type_)
            response = await self.generate_completion(prompt)
            
            assignment = {
                'id': idx,
                'type': type_,
                **self._parse_assignment_response(response, type_)
            }
            assignments.append(assignment)
        
        return {
            'assignments': assignments,
            'metadata': {
                'version': 1,
                'created_at': self._get_current_timestamp()
            }
        }
    
    def _get_assignment_prompt(self, topic_name: str, assignment_type: str) -> str:
        """과제 생성을 위한 프롬프트 반환"""
        prompts = {
            'concept': f"""
                {topic_name}에 대한 가장 기초적인 개념을 테스트하는 객관식 문제를 생성해주세요.
                비전공자가 처음 프로그래밍을 배우는 상황임을 고려하여, 매우 쉽고 명확한 문제를 만들어주세요.
                이론 수업에서 처음 배운 핵심 개념을 확인하는 문제여야 합니다.
                문제는 한 문장으로 간단하게 작성해주세요.
                다음 형식으로 반환해주세요:
                {{
                    "content": "문제 내용",
                    "choices": ["보기1", "보기2", "보기3", "보기4"],
                    "correct_answer": "정답 번호(1-4)",
                    "hint": "힌트 내용"
                }}
            """,
            'theory_concept': f"""
                {topic_name}의 실용적인 개념을 테스트하는 객관식 문제를 생성해주세요.
                비전공자도 쉽게 이해할 수 있는 실생활 예시를 활용하여 문제를 만들어주세요.
                이론 수업에서 배운 개념이 실습에서 어떻게 활용되는지 연결하는 문제를 만들어주세요.
                문제는 다음과 같은 구조로 작성해주세요:
                1. 실생활 예시로 개념 설명 (2-3문장)
                2. 파이썬 코드 예시 (2-3줄)
                3. 문제 질문 (1문장)
                
                코드를 포함할 때는 <br>와 <code> 태그를 사용해주세요. 예시:
                "content": "개념 설명...<br><br>다음 코드를 보고...<br><br><code>코드 첫째줄<br>코드 둘째줄</code>"
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
            'implementation_basic': f"""
                {topic_name}에 대한 첫 번째 기초 구현 문제를 생성해주세요.
                프로그래밍을 처음 배우는 비전공자를 위한 매우 기초적인 문제를 만들어주세요.
                문제는 2-3줄 정도의 매우 간단한 코드로 해결할 수 있어야 합니다.
                숫자 입력과 출력을 다루는 매우 간단한 문제를 만들어주세요.
                문제 설명은 한 문장으로 명확하게 작성해주세요.
                테스트 케이스는 입력과 출력이 명확하게 보이도록 작성해주세요.
                힌트는 필요한 함수와 사용 방법을 구체적으로 설명해주세요.
                다음 형식으로 반환해주세요:
                {{
                    "content": "구현할 내용 설명",
                    "test_cases": [
                        {{"input": "테스트 입력값", "output": "기대 출력값"}},
                        {{"input": "테스트 입력값", "output": "기대 출력값"}}
                    ],
                    "hint": "힌트 내용"
                }}
            """,
            'implementation_basic2': f"""
                {topic_name}에 대한 두 번째 기초 구현 문제를 생성해주세요.
                프로그래밍을 처음 배우는 비전공자를 위한 매우 기초적인 문제를 만들어주세요.
                문제는 2-3줄 정도의 매우 간단한 코드로 해결할 수 있어야 합니다.
                문자열 입력과 출력을 다루는 매우 간단한 문제를 만들어주세요.
                문제 설명은 한 문장으로 명확하게 작성해주세요.
                테스트 케이스는 입력과 출력이 명확하게 보이도록 작성해주세요.
                힌트는 필요한 함수와 사용 방법을 구체적으로 설명해주세요.
                다음 형식으로 반환해주세요:
                {{
                    "content": "구현할 내용 설명",
                    "test_cases": [
                        {{"input": "테스트 입력값", "output": "기대 출력값"}},
                        {{"input": "테스트 입력값", "output": "기대 출력값"}}
                    ],
                    "hint": "힌트 내용"
                }}
            """
        }
        return prompts[assignment_type]

    def _parse_assignment_response(self, response: str, assignment_type: str) -> Dict[str, Any]:
        """LLM 응답을 파싱하여 과제 데이터로 변환"""
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return self._get_default_assignment(assignment_type)
    
    def _get_default_assignment(self, assignment_type: str) -> Dict[str, Any]:
        """기본 과제 템플릿 반환"""
        if assignment_type in ['concept', 'theory_concept', 'metaphor']:
            return {
                'content': '문제를 준비 중입니다.',
                'choices': ['준비 중'] * 4,
                'correct_answer': '1',
                'hint': '준비 중입니다.'
            }
        defaults = {
            'implementation_basic': {
                'content': '문제를 준비 중입니다.',
                'test_cases': [{'input': '', 'output': ''}],
                'hint': '준비 중입니다.'
            },
            'implementation_basic2': {
                'content': '문제를 준비 중입니다.',
                'test_cases': [{'input': '', 'output': ''}],
                'hint': '준비 중입니다.'
            }
        }
        return defaults[assignment_type]

    async def generate(self, topic_id: str) -> str:
        """과제 내용 생성"""
        # 이론과 실습 내용 참조
        theory_file = self.data_dir / topic_id / 'current' / 'theory.json'
        practice_file = self.data_dir / topic_id / 'current' / 'practice.json'
        
        theory_content = ""
        practice_content = ""
        
        if theory_file.exists():
            with open(theory_file, 'r', encoding='utf-8') as f:
                theory_data = json.load(f)
                theory_content = theory_data['content']
        
        if practice_file.exists():
            with open(practice_file, 'r', encoding='utf-8') as f:
                practice_data = json.load(f)
                practice_content = practice_data['content']

        # 과제 내용 생성을 위한 입력 구성
        input_data = {
            "theory_content": theory_content,
            "practice_content": practice_content,
            "topic": topic_id
        }

        # 과제 내용 생성
        messages = [{
            "role": "system",
            "content": """당신은 Python 과제 생성 튜터입니다.
이론과 실습 내용을 참조하여 다음과 같은 HTML 형식으로 과제를 생성해주세요:

<div class="space-y-8">
    <!-- 개념 이해 문제 -->
    <section class="bg-white rounded-lg shadow-sm p-6">
        <h2 class="text-lg font-semibold text-gray-800 mb-4">개념 이해</h2>
        <div class="prose max-w-none text-gray-600">
            <p>{개념 문제}</p>
            <div class="mt-4 space-y-2">
                <div class="flex items-center">
                    <input type="radio" name="q1" value="0" class="mr-2">
                    <label>{보기 1}</label>
                </div>
                ...
            </div>
            <button onclick="submitQuiz(1, 'concept')" class="mt-6 w-full px-6 py-3 bg-gradient-to-r from-amber-500 to-yellow-400 text-white font-semibold rounded-xl shadow-md hover:shadow-lg transform hover:-translate-y-0.5 transition-all duration-200 hover:from-amber-600 hover:to-yellow-500 flex items-center justify-center">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                개념 이해 제출하기
            </button>
            <div id="result1" class="mt-4 hidden">
                <div class="p-4 rounded-lg"></div>
            </div>
        </div>
    </section>

    <!-- 코드 분석 문제 -->
    <section class="bg-white rounded-lg shadow-sm p-6">
        <h2 class="text-lg font-semibold text-gray-800 mb-4">코드 분석</h2>
        <div class="prose max-w-none text-gray-600">
            <p>{분석 문제}</p>
            <div class="bg-gray-900 rounded-lg p-4 my-4">
                <pre class="text-white font-mono text-sm overflow-x-auto">
{분석할 코드}
                </pre>
            </div>
            <div class="code-editor-container">
                <div id="editor2" class="code-editor"></div>
            </div>
            <button onclick="submitQuiz(2, 'analysis')" class="mt-6 w-full px-6 py-3 bg-gradient-to-r from-amber-500 to-yellow-400 text-white font-semibold rounded-xl shadow-md hover:shadow-lg transform hover:-translate-y-0.5 transition-all duration-200 hover:from-amber-600 hover:to-yellow-500 flex items-center justify-center">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                코드 분석 제출하기
            </button>
            <div id="result2" class="mt-4 hidden">
                <div class="p-4 rounded-lg"></div>
            </div>
        </div>
    </section>

    <!-- 코드 구현 문제 -->
    <section class="bg-white rounded-lg shadow-sm p-6">
        <h2 class="text-lg font-semibold text-gray-800 mb-4">코드 구현</h2>
        <div class="prose max-w-none text-gray-600">
            <p>{구현 문제}</p>
            <div class="code-editor-container">
                <div id="editor3" class="code-editor"></div>
            </div>
            <div class="mt-4">
                <p>테스트 케이스:</p>
                <ul class="list-disc list-inside">
                    <li>입력: {입력값} → 출력: {기대값}</li>
                    ...
                </ul>
            </div>
            <button onclick="submitQuiz(3, 'implementation')" class="mt-6 w-full px-6 py-3 bg-gradient-to-r from-amber-500 to-yellow-400 text-white font-semibold rounded-xl shadow-md hover:shadow-lg transform hover:-translate-y-0.5 transition-all duration-200 hover:from-amber-600 hover:to-yellow-500 flex items-center justify-center">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                코드 구현 제출하기
            </button>
            <div id="result3" class="mt-4 hidden">
                <div class="p-4 rounded-lg"></div>
            </div>
        </div>
    </section>
</div>"""
        }, {
            "role": "user",
            "content": f"""# 입력 데이터
{json.dumps(input_data, indent=2, ensure_ascii=False)}"""
        }]
        
        response = await self.llm.agenerate([messages])
        response_text = response.generations[0][0].text
        
        # 응답 정제
        if "# 출력 데이터" in response_text:
            response_text = response_text.replace("# 출력 데이터\n", "")
        
        # JSON 형식이면 파싱
        if response_text.strip().startswith("{"):
            try:
                data = json.loads(response_text)
                if "assignment_content" in data:
                    html_content = data["assignment_content"]
                else:
                    html_content = response_text
            except json.JSONDecodeError:
                html_content = response_text
        else:
            html_content = response_text
        
        # HTML 형식 확인
        if not html_content.strip().startswith("<div"):
            html_content = f"""
<div class="space-y-8">
    {html_content}
</div>
"""
        
        # 저장 및 반환
        assignment_file = self.data_dir / topic_id / 'current' / 'assignment.json'
        assignment_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(assignment_file, 'w', encoding='utf-8') as f:
            json.dump({
                'content': html_content,
                'metadata': {
                    'created_at': datetime.now().isoformat(),
                    'version': 1
                }
            }, f, indent=2, ensure_ascii=False)

        return html_content

    async def analyze(self, submission: str) -> Dict[str, Any]:
        """과제 제출물 분석"""
        return {
            'code_quality': 'good',
            'test_results': [],
            'feedback': '잘 작성되었습니다.'
        } 