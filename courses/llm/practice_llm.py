from datetime import datetime
from pathlib import Path
import json
import re
from typing import Dict, Any, List, Union

from .base_llm import BaseLLM
from courses.agents.practice_analysis_agent import PracticeAnalysisAgent

class PracticeLLM(BaseLLM):
    def __init__(self, model_name="gpt-4", temperature=0.7):
        super().__init__(model_name, temperature)
        self.data_dir = self.base_dir / 'data' / 'topics'
        self.prompt_template = self.load_prompt('practice_llm_prompt.md')
        self.analysis_agent = PracticeAnalysisAgent()

    def _extract_key_concepts(self, theory_content: str) -> Dict[str, List]:
        """이론 내용에서 핵심 개념 추출"""
        concepts = re.findall(r'<b>(.*?)</b>', theory_content)
        terms = re.findall(r'<span style=\'color: #0066cc;\'>(.*?)</span>', theory_content)
        examples = re.findall(
            r'<div class="bg-gray-900.*?<pre.*?>(.*?)</pre>.*?<p class="text-green-400.*?># 실행 결과: (.*?)</p>', 
            theory_content, 
            re.DOTALL
        )
        return {
            'concepts': list(set(concepts)),
            'terms': list(set(terms)),
            'examples': examples
        }

    def _extract_example_code(self, theory_content: str, topic_id: str) -> str:
        """이론 내용에서 예제 코드 추출"""
        code_blocks = re.findall(r'```python\s*(.*?)\s*```', theory_content, re.DOTALL)
        if code_blocks:
            return code_blocks[0].strip()
        
        example_blocks = re.findall(r'<div class="bg-gray-900.*?<pre.*?>(.*?)</pre>', theory_content, re.DOTALL)
        if example_blocks:
            return example_blocks[0].strip()
        
        return "print('예제를 찾을 수 없습니다.')"

    async def generate(self, topic_id: str) -> str:
        """실습 내용 생성"""
        theory_file = self.data_dir / topic_id / 'content' / 'theory.html'
        theory_content = ""
        
        if theory_file.exists():
            with open(theory_file, 'r', encoding='utf-8') as f:
                theory_content = f.read()

        practice_info = {
            "file_name": f"{topic_id}_practice.py",
            "setup_steps": [
                "VSCode 실행",
                "새 파일 만들기",
                "Python 파일로 저장",
                "코드 작성 및 실행"
            ]
        }

        input_data = {
            "theory_content": theory_content,
            "topic": topic_id,
            "practice_info": practice_info
        }

        messages = [
            {
                "role": "system",
                "content": self.prompt_template
            },
            {
                "role": "user",
                "content": f"다음 입력 데이터를 바탕으로 실습 내용을 생성해주세요:\n{json.dumps(input_data, ensure_ascii=False, indent=2)}"
            }
        ]

        response = await self.llm.agenerate([messages])
        practice_content = response.generations[0][0].text

        metadata = f"""<!-- 
메타데이터:
created_at: {datetime.now().isoformat()}
version: 1
key_concepts: {self._extract_key_concepts(theory_content)}
-->
"""
        practice_content = f"{metadata}\n{practice_content}"

        practice_file = self.data_dir / topic_id / 'content' / 'practice.html'
        practice_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(practice_file, 'w', encoding='utf-8') as f:
            f.write(practice_content)

        return practice_content

    def _create_practice_prompt(self, topic: str, theory_content: str, prompt_template: str) -> List[Dict[str, str]]:
        """프롬프트 생성"""
        return [{
            "role": "user",
            "content": f"다음 주제와 이론 내용을 바탕으로 실습 내용을 생성해주세요:\n\n주제: {topic}\n\n이론 내용:\n{theory_content}\n\n{prompt_template}"
        }]

    async def analyze(self, submission: Union[str, bytes], topic_id: str, submission_type: str = 'image') -> Dict[str, Any]:
        """실습 제출물 분석"""
        try:
            if submission_type == 'image':
                theory_file = self.data_dir / topic_id / 'content' / 'theory.html'
                example_code = ""
                
                if theory_file.exists():
                    with open(theory_file, 'r', encoding='utf-8') as f:
                        theory_content = f.read()
                        example_code = self._extract_example_code(theory_content, topic_id)

                return await self.analysis_agent.analyze_practice_image(
                    topic_id=topic_id,
                    image_data=submission,
                    reference_code=example_code
                )
            
            return await self.analysis_agent.analyze_practice_code(submission)
            
        except Exception as e:
            return {
                'success': False,
                'error': f'분석 중 오류 발생: {str(e)}'
            }