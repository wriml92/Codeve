from pathlib import Path
import json
import re
from typing import Dict, Any, List

from asgiref.sync import sync_to_async
from langchain_core.messages import SystemMessage, HumanMessage

from .base_llm import BaseLLM
from ..models import TheoryContent

class TheoryLLM(BaseLLM):
    def __init__(self, model_name="gpt-4", temperature=0.7):
        super().__init__(model_name, temperature)
        self.data_dir = self.base_dir / 'data' / 'topics'
        self.prompt_template = self.load_prompt('theory_llm_prompt.md')
        self.example_patterns = self._init_example_patterns()

    def _init_example_patterns(self) -> Dict[str, Dict[str, Any]]:
        """토픽별 예제 코드 패턴 정의"""
        return {
            'input_output': {
                'structure': ['input(', 'print('],
                'output_pattern': r'안녕하세요.*!',
                'required_elements': ['input', 'print', '사용자 입력']
            },
            'variables': {
                'structure': ['=', 'print('],
                'output_pattern': r'결과.*입니다.*!',
                'required_elements': ['변수 할당', '출력']
            },
            'operators': {
                'structure': ['+', '-', '*', '/', 'print('],
                'output_pattern': r'계산 결과.*',
                'required_elements': ['산술 연산자', '출력']
            },
            'tuples': {
                'structure': ['(', ',', ')', '='],
                'output_pattern': r'튜플.*결과.*',
                'required_elements': ['튜플 생성', '튜플 접근', '튜플 언패킹']
            },
            'dictionaries': {
                'structure': ['{', ':', '}', '=', '[]'],
                'output_pattern': r'딕셔너리.*결과.*',
                'required_elements': ['딕셔너리 생성', '키로 접근', '값 수정', '키-값 쌍']
            },
            'conditionals': {
                'structure': ['if', 'else', ':', '==', 'print('],
                'output_pattern': r'조건.*결과.*',
                'required_elements': ['if문', 'else문', '조건식', '들여쓰기']
            },
            'loops': {
                'structure': ['for', 'in', 'range', 'while', 'break', 'continue'],
                'output_pattern': r'반복.*실행.*',
                'required_elements': ['for문', 'while문', '반복 조건', '반복 제어']
            },
            'functions': {
                'structure': ['def', '()', 'return', 'parameter', 'argument'],
                'output_pattern': r'함수.*호출.*',
                'required_elements': ['함수 정의', '매개변수', '반환값', '함수 호출']
            },
            'classes': {
                'structure': ['class', '__init__', 'self', 'method', 'attribute'],
                'output_pattern': r'객체.*생성.*',
                'required_elements': ['클래스 정의', '생성자', '메서드', '속성']
            },
            'modules': {
                'structure': ['import', 'from', 'as', 'package', 'module'],
                'output_pattern': r'모듈.*사용.*',
                'required_elements': ['모듈 임포트', '패키지 구조', '네임스페이스', '모듈 사용']
            },
            'exceptions': {
                'structure': ['try', 'except', 'finally', 'raise', 'Exception'],
                'output_pattern': r'예외.*처리.*',
                'required_elements': ['예외 발생', '예외 처리', '정리 작업', '사용자 정의 예외']
            },
            'file_io': {
                'structure': ['open()', 'read()', 'write()', 'close()', 'with'],
                'output_pattern': r'파일.*입출력.*',
                'required_elements': ['파일 열기', '파일 읽기', '파일 쓰기', '파일 관리']
            }
        }

    async def generate(self, topic_id: str) -> str:
        """이론 내용 생성"""
        messages = [
            SystemMessage(content=f"""당신은 프로그래밍을 처음 접하는 완전 초보자를 위한 Python 튜터입니다. 
현재 다루는 주제: {topic_id}

다음 원칙에 따라 최대한 쉽고 친근하게, 그리고 자세하게 설명해주세요:

1. 개념 소개 섹션
- 일상생활에서 마주치는 상황으로 시작
- 개념의 정의를 3가지 이상의 다른 방식으로 설명
- 해당 개념이 왜 필요한지 실생활 예시로 설명
- 전문 용어가 나올 때마다 괄호 안에 쉬운 설명 추가
- 개념을 처음 들었을 때 가질 수 있는 의문점들을 먼저 해소

2. 비유 섹션
- 학생들의 실생활에서 찾은 3가지 이상의 구체적인 비유 제시
- 각 비유마다 개념의 다른 측면을 설명
- 비유가 적절한 이유도 설명
- 각 비유에 대한 구체적인 예시 코드 포함
- 비유와 실제 코드의 연결점 자세히 설명

3. 실생활 응용 섹션
- 학교생활에서의 활용 예시
- 게임이나 취미 생활에서의 활용 예시
- SNS나 메시징에서의 활용 예시
- 각 예시마다 실제 코드로 어떻게 구현하는지 설명
- 학생들이 직접 응용해볼 수 있는 아이디어 제안

4. 코드 예제 섹션
- 가장 기본적인 사용법부터 시작
- 하나의 개념을 여러 가지 방식으로 사용하는 예제
- 자주 사용되는 패턴 소개
- 각 예제마다 실행 결과와 함께 자세한 설명
- 예제를 변형해서 시도해볼 수 있는 방법 제안

5. 핵심 포인트 섹션
- 반드시 기억해야 할 내용 3-4가지 정리
- 각 포인트마다 "이것만은 기억하세요!"와 같은 강조
- 포인트마다 간단한 예시 코드 추가
- 해당 포인트를 잊었을 때 생길 수 있는 문제 설명
- 포인트를 기억하기 쉽게 만드는 팁 제공

6. 주의사항 섹션
- 초보자가 자주 저지르는 실수 3가지 이상 설명
- 각 실수에 대한 구체적인 예시 코드
- 실수했을 때 발생하는 오류 메시지 설명
- 문제 해결 방법을 단계별로 안내
- 실수를 방지하는 팁과 요령 제시

7. 연습하기 섹션
- 배운 내용을 연습할 수 있는 3가지 예제
- 난이도별로 구분된 연습문제
- 각 예제의 예상 결과 미리 제시
- 힌트와 해결 방법 단계별 안내
- 성공적으로 해결했을 때의 확인 포인트

토픽별 설명 포인트:
- input_output: 입력과 출력이 마치 대화하는 것과 같다고 설명
- variables: 변수를 상자나 라벨이 붙은 컵에 비유
- operators: 계산기 버튼이나 수학 시간의 연산에 비유
- strings: 글자를 한 줄로 이어놓은 실에 비유
- lists: 책장이나 서랍에 물건 정리하는 것에 비유
- functions: 요리 레시피나 자판기 작동 방식에 비유
- loops: 운동 반복하기나 악기 연습하기에 비유
- conditionals: 신호등이나 날씨에 따른 옷차림에 비유

응답은 반드시 HTML 형식으로 작성해주세요. 다음 구조를 엄격히 따라주세요:
<div class="space-y-8">
    <section class="mb-8">
        <h2 class="text-lg font-semibold text-black-600 mb-3">섹션 제목</h2>
        <p class="text-gray-800 leading-relaxed">내용</p>
    </section>
    ...
</div>"""),
            HumanMessage(content=f"""# 입력 데이터
{{
    "topic": "{topic_id}"
}}

{self.prompt_template}""")
        ]
        
        response = await self.llm.agenerate([messages])
        content = response.generations[0][0].text
        
        example_code = self._extract_example_code(content)
        if example_code and not self._validate_example_code(example_code, topic_id):
            return await self.generate(topic_id)
        
        await sync_to_async(TheoryContent.objects.update_or_create)(
            topic_id=topic_id,
            defaults={'content': content}
        )
        
        return content

    def _extract_example_code(self, content: str) -> str:
        """이론 내용에서 예제 코드 추출"""
        code_blocks = re.findall(r'```python\s*(.*?)\s*```', content, re.DOTALL)
        return code_blocks[0] if code_blocks else ""

    def _validate_example_code(self, code: str, topic_id: str) -> bool:
        """예제 코드가 토픽별 패턴에 맞는지 검증"""
        if topic_id not in self.example_patterns:
            return True
            
        pattern = self.example_patterns[topic_id]
        
        for struct in pattern['structure']:
            if struct not in code:
                return False
                
        if not re.search(pattern['output_pattern'], code):
            return False
            
        for element in pattern['required_elements']:
            if element == '사용자 입력' and 'input(' not in code:
                return False
            elif element == '변수 할당' and not re.search(r'\w+\s*=', code):
                return False
            elif element == '산술 연산자' and not re.search(r'[+\-*/]', code):
                return False
            elif element == '출력' and 'print(' not in code:
                return False
                
        return True

    def _format_response(self, content: str) -> str:
        """HTML 형식으로 응답 포맷팅"""
        return f'<div class="space-y-8">{content}</div>'
        
    async def analyze(self, content: str) -> Dict[str, Any]:
        """이론 내용 분석"""
        return {
            'sections': self._parse_sections(content),
            'example_code': self._extract_example_code(content),
            'key_concepts': self._extract_key_concepts(content)
        }

    def _parse_sections(self, content: str) -> List[str]:
        """섹션 파싱"""
        sections = []
        current_section = []
        
        for line in content.split('\n'):
            if line.startswith('##'):
                if current_section:
                    sections.append('\n'.join(current_section))
                current_section = [line]
            else:
                current_section.append(line)
                
        if current_section:
            sections.append('\n'.join(current_section))
            
        return sections

    def _extract_key_concepts(self, content: str) -> List[str]:
        """핵심 개념 추출"""
        concepts = []
        concepts.extend(re.findall(r'<b>(.*?)</b>', content))
        concepts.extend(re.findall(r'<span style=\'color: #0066cc;\'>(.*?)</span>', content))
        return list(set(concepts))