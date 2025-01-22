from typing import Dict, Any
from .base_llm import BaseLLM
import json
from pathlib import Path
from datetime import datetime

class AssignmentLLM(BaseLLM):
    def __init__(self, model_name="gpt-4", temperature=0.7):
        super().__init__(model_name, temperature)
        self.data_dir = self.base_dir / 'data' / 'topics'
        self.prompt_template = self.load_prompt('assignment_llm_prompt.md')

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
            <div class="mt-4">
                <p>테스트 케이스:</p>
                <ul class="list-disc list-inside">
                    <li>입력: {입력값} → 출력: {기대값}</li>
                    ...
                </ul>
            </div>
        </div>
    </section>

    <!-- 코드 구현 문제 -->
    <section class="bg-white rounded-lg shadow-sm p-6">
        <h2 class="text-lg font-semibold text-gray-800 mb-4">코드 구현</h2>
        <div class="prose max-w-none text-gray-600">
            <p>{구현 문제}</p>
            <div class="bg-gray-900 rounded-lg p-4 my-4">
                <pre class="text-white font-mono text-sm overflow-x-auto">
{초기 코드}
                </pre>
            </div>
            <div class="mt-4">
                <p>테스트 케이스:</p>
                <ul class="list-disc list-inside">
                    <li>입력: {입력값} → 출력: {기대값}</li>
                    ...
                </ul>
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