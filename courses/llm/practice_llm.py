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

        # 실습 내용 생성을 위한 입력 구성
        input_data = {
            "theory_content": theory_content,
            "topic": topic_id
        }

        # 실습 내용 생성
        messages = [{
            "role": "system",
            "content": """당신은 Python 실습 튜터입니다. 
이론 내용을 참조하여 VSCode에서 실습할 수 있는 내용을 HTML 형식으로 생성해주세요.

반드시 다음 HTML 구조를 사용하여 응답해야 합니다:

<div class="space-y-8">
    <!-- 실습 설명 -->
    <section class="bg-white rounded-lg shadow-sm p-6">
        <h2 class="text-lg font-semibold text-gray-800 mb-4">실습 설명</h2>
        <div class="prose max-w-none text-gray-600">
            {이론 내용에서 설명한 개념을 실습으로 풀어서 설명}
        </div>
    </section>

    <!-- 예제 코드 -->
    <section class="bg-white rounded-lg shadow-sm p-6">
        <h2 class="text-lg font-semibold text-gray-800 mb-4">예제 코드</h2>
        <div class="bg-gray-900 rounded-lg p-4">
            <pre class="text-white font-mono text-sm overflow-x-auto">
{이론에서 제시된 예제 코드를 포함한 실행 가능한 코드}
            </pre>
        </div>
        <div class="mt-4 text-sm text-gray-500">
            <p>* 코드를 복사하여 VSCode에 붙여넣기 할 수 있습니다.</p>
        </div>
    </section>

    <!-- 실행 방법 -->
    <section class="bg-white rounded-lg shadow-sm p-6">
        <h2 class="text-lg font-semibold text-gray-800 mb-4">실행 방법</h2>
        <ol class="list-decimal list-inside space-y-3 text-gray-600">
            <li class="pl-2">VSCode에서 새 파일 만들기</li>
            <li class="pl-2">위의 예제 코드를 입력하기</li>
            <li class="pl-2">파일을 .py 확장자로 저장하기</li>
            <li class="pl-2">코드 실행 후 결과 확인하기</li>
        </ol>
    </section>

    <!-- 주의사항 -->
    <section class="bg-white rounded-lg shadow-sm p-6">
        <h2 class="text-lg font-semibold text-gray-800 mb-4">주의사항</h2>
        <ul class="list-disc list-inside space-y-3 text-gray-600">
            {이론 내용에서 언급된 주의사항 및 실행 시 유의점}
        </ul>
    </section>
</div>"""
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
    
