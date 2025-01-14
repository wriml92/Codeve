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
        # data 디렉토리 생성
        self.data_dir = Path(__file__).parent.parent / 'data' / 'practice'
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # course_list.json 파일 경로
        self.course_list_path = Path(__file__).parent.parent / 'agents' / 'course_list.json'
        
        # 프롬프트 파일 경로
        self.prompt_path = Path(__file__).parent.parent / 'agent_docs' / 'agent_prompt' / 'practice_llm_prompt.md'
        
        # theory 데이터 디렉토리
        self.theory_dir = Path(__file__).parent.parent / 'data' / 'theory'

    async def generate(self, topic: str) -> str:
        """주어진 주제에 대한 실습 내용 생성"""
        # 프롬프트 읽기
        with open(self.prompt_path, 'r', encoding='utf-8') as f:
            prompt_template = f.read()
            
        # course_list.json 읽기
        with open(self.course_list_path, 'r', encoding='utf-8') as f:
            course_list = json.load(f)
            
        # 각 코스의 토픽에 대해 실습 내용 생성
        for course_id, course_data in course_list.items():
            for topic in course_data['topics']:
                topic_id = topic['id']
                file_path = self.data_dir / f"{topic_id}.json"
                
                # 기존 파일이 있으면 백업
                if file_path.exists():
                    backup_dir = self.data_dir / 'backup'
                    backup_dir.mkdir(exist_ok=True)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    backup_path = backup_dir / f"{topic_id}_{timestamp}.json"
                    shutil.copy2(file_path, backup_path)
                    print(f"백업 완료: {backup_path}")
                
                # 해당 토픽의 이론 내용 읽기
                theory_file = self.theory_dir / f"{topic_id}.json"
                if not theory_file.exists():
                    print(f"Warning: Theory content not found for {topic_id}")
                    continue
                    
                with open(theory_file, 'r', encoding='utf-8') as f:
                    theory_data = json.load(f)
                
                # LLM으로 실습 내용 생성
                messages = self._create_practice_prompt(
                    topic['name'], 
                    theory_data['content'],
                    prompt_template
                )
                response = await self.llm.agenerate([messages])
                practice_content = response.generations[0][0].text
                
                # JSON 형식으로 저장
                practice_data = {
                    'topic_id': topic_id,
                    'topic_name': topic['name'],
                    'content': practice_content,
                    'course_id': course_id,
                    'theory_based_on': theory_data['content']
                }
                
                # 파일 저장
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(practice_data, f, ensure_ascii=False, indent=2)
                    
                print(f"생성 완료: {file_path}")
    
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
    
