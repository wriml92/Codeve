from typing import Dict, Any
from .base_llm import BaseLLM

class PracticeLLM(BaseLLM):
    async def generate(self, theory_content: str) -> str:
        """이론 내용 기반으로 실습 문제 생성"""
        messages = self._create_practice_prompt(theory_content)
        response = await self.llm.agenerate([messages])
        return response.generations[0][0].text
    
    async def analyze(self, submission: str) -> Dict[str, Any]:
        """실습 제출물 분석"""
        return {
            'code_quality': self._analyze_code_quality(submission),
            'test_results': self._run_test_cases(submission),
            'feedback': self._generate_feedback(submission)
        } 
    
