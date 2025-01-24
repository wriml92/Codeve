from typing import Dict, Any, List
from .base_llm import BaseLLM
from ..models import TheoryContent
from asgiref.sync import sync_to_async
import re

class TheoryLLM(BaseLLM):
    def __init__(self, model_name="gpt-4", temperature=0.7):
        super().__init__(model_name, temperature)
        self.data_dir = self.base_dir / 'data' / 'topics'
        self.prompt_template = self.load_prompt('theory_llm_prompt.md')
        
        # 토픽별 예제 코드 패턴 정의
        self.example_patterns = {
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
            }
        }

    async def generate(self, topic_id: str) -> str:
        """이론 내용 생성"""
        messages = [{
            "role": "system",
            "content": f"""당신은 비전공자를 위한 Python 이론 튜터입니다.
현재 다루는 주제: {topic_id}

예제 코드 작성 시 다음 규칙을 반드시 따라주세요:
1. 코드는 매우 기초적이고 직관적이어야 합니다 (2-3줄)
2. 각 줄마다 자세한 한글 주석을 포함해야 합니다
3. 실행 결과에는 이모지를 포함하여 친근감을 줍니다
4. 예제는 ```python 블록으로 감싸서 제공합니다
5. 예제 뒤에는 실행 결과를 주석으로 포함합니다

토픽별 필수 요소:
- input_output: input()과 print() 함수 사용
- variables: 변수 할당과 출력 포함
- operators: 기본 산술 연산자와 출력 포함"""
        }, {
            "role": "user",
            "content": f"""# 입력 데이터
{{
    "topic": "{topic_id}"
}}

{self.prompt_template}"""
        }]
        
        response = await self.llm.agenerate([messages])
        content = self._format_response(response.generations[0][0].text)
        
        # 예제 코드 검증
        example_code = self._extract_example_code(content)
        if example_code:
            is_valid = self._validate_example_code(example_code, topic_id)
            if not is_valid:
                # 예제가 패턴에 맞지 않으면 재생성
                return await self.generate(topic_id)
        
        # DB에 저장
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
        
        # 구조 검사
        for struct in pattern['structure']:
            if struct not in code:
                return False
                
        # 출력 패턴 검사
        output_pattern = pattern['output_pattern']
        if not re.search(output_pattern, code):
            return False
            
        # 필수 요소 검사
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
        return f"""<div class="space-y-8">
            {content}
        </div>"""
        
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
        
        # <b> 태그로 강조된 내용을 핵심 개념으로 추출
        concepts.extend(re.findall(r'<b>(.*?)</b>', content))
        
        # 파란색으로 표시된 전문 용어 추출
        concepts.extend(re.findall(r'<span style=\'color: #0066cc;\'>(.*?)</span>', content))
        
        # 중복 제거 및 반환
        return list(set(concepts))