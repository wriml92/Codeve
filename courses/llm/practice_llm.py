from typing import Dict, Any
from .base_llm import BaseLLM
import json
import os
from pathlib import Path
from datetime import datetime
import shutil

class PracticeLLM(BaseLLM):
    def __init__(self, model_name="gpt-4", temperature=0.7):
        super().__init__(model_name, temperature)
        self.data_dir = self.base_dir / 'data' / 'topics'
        self.prompt_template = self.load_prompt('practice_llm_prompt.md')

    async def generate(self, topic_id: str) -> str:
        """실습 내용 생성"""
        # 이론 내용 참조
        theory_file = self.data_dir / topic_id / 'current' / 'theory.json'
        if theory_file.exists():
            with open(theory_file, 'r', encoding='utf-8') as f:
                theory_data = json.load(f)
                theory_content = theory_data['content']
        else:
            theory_content = ""

        # 토픽별 실습 파일명 생성
        file_name = f"{topic_id}_practice.py"
        
        # 실습 내용 생성을 위한 입력 구성
        input_data = {
            "theory_content": theory_content,
            "topic": topic_id,
            "practice_info": {
                "file_name": file_name,
                "setup_steps": [
                    f"1. VSCode에서 새 파일을 만들고 '{file_name}'으로 저장하세요.",
                    "2. 아래 예제 코드를 파일에 복사하세요.",
                    "3. 터미널에서 'python {file_name}' 명령으로 실행하세요."
                ]
            }
        }

        # 실습 내용 생성
        messages = [{
            "role": "system",
            "content": """당신은 Python 실습 튜터입니다. 
모든 실습은 VSCode 환경에서 진행됩니다. 이론 내용을 참조하여 학생들이 VSCode에서 직접 실습할 수 있는 내용을 생성해주세요.

실습 환경:
- IDE: Visual Studio Code (VSCode)
- 실행 방법: 터미널에서 'python 파일명.py' 명령어 사용
- 파일 확장자: .py

{self.prompt_template}"""
        }, {
            "role": "user",
            "content": f"""# 입력 데이터
{json.dumps(input_data, indent=2, ensure_ascii=False)}

{self.prompt_template}"""
        }]
        
        response = await self.llm.agenerate([messages])
        practice_content = response.generations[0][0].text

        # 실습 내용 저장
        practice_file = self.data_dir / topic_id / 'current' / 'practice.json'
        practice_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(practice_file, 'w', encoding='utf-8') as f:
            json.dump({
                'content': practice_content,
                'metadata': {
                    'created_at': datetime.now().isoformat(),
                    'version': 1
                }
            }, f, indent=2, ensure_ascii=False)

        return practice_content

    def _create_practice_prompt(self, topic: str, theory_content: str, prompt_template: str) -> str:
        """프롬프트 생성"""
        return [{
            "role": "user", 
            "content": f"다음 주제와 이론 내용을 바탕으로 실습 내용을 생성해주세요:\n\n주제: {topic}\n\n이론 내용:\n{theory_content}\n\n{prompt_template}"
        }]
    
    async def analyze(self, submission: str) -> Dict[str, Any]:
        """실습 제출물 분석"""
        return {
            'code_quality': self._analyze_code_quality(submission),
            'test_results': self._run_test_cases(submission),
            'feedback': self._generate_feedback(submission)
        } 
    
