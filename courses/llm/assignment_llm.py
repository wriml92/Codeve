from typing import Dict, Any
from .base_llm import BaseLLM
import json

class AssignmentLLM(BaseLLM):
    def __init__(self, model_name="gpt-4", temperature=0.7):
        super().__init__(model_name, temperature)

    async def generate_assignment(self, topic: str) -> Dict[str, Any]:
        """주어진 주제에 대한 과제를 생성"""
        prompt = self._create_assignment_prompt(topic)
        response = await self.llm.agenerate([prompt])
        assignment_content = response.generations[0][0].text
        
        # 과제 내용에서 코드 셀을 포함한 JSON 반환
        return self._parse_assignment_content(assignment_content)

    def _create_assignment_prompt(self, topic: str) -> str:
        """과제 생성을 위한 프롬프트"""
        return f"다음 주제에 대한 과제를 생성해주세요: {topic}"

    def _parse_assignment_content(self, content: str) -> Dict[str, Any]:
        """과제 내용을 파싱하여 코드 셀과 텍스트로 분리"""
        # 예시: JSON 형식으로 과제 내용 파싱
        try:
            assignment_data = json.loads(content)
            return {
                'description': assignment_data.get('description', ''),
                'code_cell': assignment_data.get('code_cell', ''),
                'test_cases': assignment_data.get('test_cases', [])
            }
        except json.JSONDecodeError:
            raise ValueError("과제 내용이 올바른 JSON 형식이 아닙니다.") 