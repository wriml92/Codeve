from typing import Dict, Any, List
from .base_llm import BaseLLM
import json
import os
from pathlib import Path

class TheoryLLM(BaseLLM):
    def __init__(self, model_name="gpt-4", temperature=0.7):
        super().__init__(model_name, temperature)
        self.data_dir = self.base_dir / 'data' / 'topics'
        self.prompt_template = self.load_prompt('theory_llm_prompt.md')

    async def generate(self, topic_id: str) -> str:
        """이론 내용 생성"""
        messages = [{
            "role": "user",
            "content": f"""# 입력 데이터
{{
    "topic": "{topic_id}"
}}

{self.prompt_template}"""
        }]
        
        response = await self.llm.agenerate([messages])
        return response.generations[0][0].text
        
    async def analyze(self, content: str) -> Dict[str, Any]:
        """이론 내용 분석"""
        return {
            'sections': self._parse_sections(content),
            'complexity_level': self._analyze_complexity(content),
            'key_concepts': self._extract_key_concepts(content)
        }

    def _parse_sections(self, content: str) -> List[str]:
        """섹션 파싱"""
        # 섹션 파싱 로직 구현
        pass

    def _analyze_complexity(self, content: str) -> str:
        """복잡도 분석"""
        # 복잡도 분석 로직 구현
        pass

    def _extract_key_concepts(self, content: str) -> List[str]:
        """핵심 개념 추출"""
        # 핵심 개념 추출 로직 구현
        pass

# theory_llm.py의 프롬프트 템플릿 예시
THEORY_TEMPLATE = """
# {topic_name}

## 개념 소개
{concept_description}

## 비유로 이해하기
{analogy}

```python
{code_example}
# 출력 결과: {output}
```

## 핵심 포인트
- {key_point_1}
- {key_point_2}
- {key_point_3}

## 주의사항
1. {caution_1}
2. {caution_2}
3. {caution_3}
""" 