from typing import Dict, Any
from .base_llm import BaseLLM

class TheoryLLM(BaseLLM):
    async def generate(self, topic: str) -> str:
        """주어진 주제에 대한 이론 설명 생성"""
        messages = self._create_theory_prompt(topic)
        response = await self.llm.agenerate([messages])
        return response.generations[0][0].text
    
    async def analyze(self, content: str) -> Dict[str, Any]:
        """이론 내용 분석 및 섹션 추출"""
        return {
            'sections': self._parse_sections(content),
            'complexity_level': self._analyze_complexity(content),
            'key_concepts': self._extract_key_concepts(content)
        } 