from typing import Dict, Any
from .base_llm import BaseLLM
import json
import os
from pathlib import Path

class TheoryLLM(BaseLLM):
    def __init__(self, model_name="gpt-4", temperature=0.7):
        super().__init__(model_name, temperature)
        # data 디렉토리 생성
        self.data_dir = Path(__file__).parent.parent / 'data' / 'theory'
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # course_list.json 파일 경로
        self.course_list_path = Path(__file__).parent.parent / 'agents' / 'course_list.json'
        
        # 프롬프트 파일 경로
        self.prompt_path = Path(__file__).parent.parent / 'agent_docs' / 'agent_prompt' / 'theory_llm_prompt.md'

    async def generate(self, topic: str) -> str:
        """주어진 주제에 대한 이론 설명 생성"""
        # 프롬프트 읽기
        with open(self.prompt_path, 'r', encoding='utf-8') as f:
            prompt_template = f.read()
            
        # course_list.json 읽기
        with open(self.course_list_path, 'r', encoding='utf-8') as f:
            course_list = json.load(f)
            
        # 각 코스의 토픽에 대해 이론 내용 생성
        for course_id, course_data in course_list.items():
            for topic in course_data['topics']:
                topic_id = topic['id']
                
                # LLM으로 이론 내용 생성
                messages = self._create_theory_prompt(topic['name'], prompt_template)
                response = await self.llm.agenerate([messages])
                theory_content = response.generations[0][0].text
                
                # JSON 형식으로 저장
                theory_data = {
                    'topic_id': topic_id,
                    'topic_name': topic['name'],
                    'content': theory_content,
                    'course_id': course_id
                }
                
                # 파일 저장
                file_path = self.data_dir / f"{topic_id}.json"
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(theory_data, f, ensure_ascii=False, indent=2)
                    
                print(f"생성 완료: {file_path}")
    
    async def analyze(self, content: str) -> Dict[str, Any]:
        """이론 내용 분석 및 섹션 추출"""
        return {
            'sections': self._parse_sections(content),
            'complexity_level': self._analyze_complexity(content),
            'key_concepts': self._extract_key_concepts(content)
        }
        
    def _create_theory_prompt(self, topic: str, prompt_template: str) -> str:
        """프롬프트 생성"""
        return [{"role": "user", "content": f"다음 주제에 대해 설명해주세요: {topic}\n\n{prompt_template}"}] 