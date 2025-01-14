from typing import Dict, Any
from .base_llm import BaseLLM
import json
import os
from pathlib import Path
from datetime import datetime

class AssignmentLLM(BaseLLM):
    def __init__(self, model_name="gpt-4", temperature=0.7):
        super().__init__(model_name, temperature)
        # data 디렉토리 생성
        self.data_dir = Path(__file__).parent.parent / 'data' / 'assignment'
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # course_list.json 파일 경로
        self.course_list_path = Path(__file__).parent.parent / 'agents' / 'course_list.json'
        
        # 프롬프트 파일 경로
        self.prompt_path = Path(__file__).parent.parent / 'agent_docs' / 'agent_prompt' / 'assignment_llm_prompt.md'
        
        # theory와 practice 데이터 디렉토리
        self.theory_dir = Path(__file__).parent.parent / 'data' / 'theory'
        self.practice_dir = Path(__file__).parent.parent / 'data' / 'practice'

    async def generate(self, topic: str) -> str:
        """주어진 주제에 대한 과제 내용 생성"""
        # 프롬프트 읽기
        with open(self.prompt_path, 'r', encoding='utf-8') as f:
            prompt_template = f.read()
            
        # course_list.json 읽기
        with open(self.course_list_path, 'r', encoding='utf-8') as f:
            course_list = json.load(f)
            
        # 각 코스의 토픽에 대해 과제 내용 생성
        for course_id, course_data in course_list.items():
            for topic in course_data['topics']:
                topic_id = topic['id']
                
                # 해당 토픽의 이론과 실습 내용 읽기
                theory_file = self.theory_dir / f"{topic_id}.json"
                practice_file = self.practice_dir / f"{topic_id}.json"
                
                if not theory_file.exists() or not practice_file.exists():
                    print(f"Warning: Theory or practice content not found for {topic_id}")
                    continue
                    
                with open(theory_file, 'r', encoding='utf-8') as f:
                    theory_data = json.load(f)
                with open(practice_file, 'r', encoding='utf-8') as f:
                    practice_data = json.load(f)
                
                # LLM으로 과제 내용 생성
                messages = self._create_assignment_prompt(
                    topic['name'],
                    theory_data['content'],
                    practice_data['content'],
                    prompt_template
                )
                response = await self.llm.agenerate([messages])
                assignment_content = response.generations[0][0].text
                
                # JSON 형식으로 저장
                assignment_data = {
                    'topic_id': topic_id,
                    'topic_name': topic['name'],
                    'content': assignment_content,
                    'course_id': course_id,
                    'theory_based_on': theory_data['content'],
                    'practice_based_on': practice_data['content']
                }
                
                # 파일 저장
                file_path = self.data_dir / f"{topic_id}.json"
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(assignment_data, f, ensure_ascii=False, indent=2)
                    
                print(f"생성 완료: {file_path}")
    
    def _create_assignment_prompt(self, topic: str, theory_content: str, practice_content: str, prompt_template: str) -> str:
        """프롬프트 생성"""
        # 이론 내용에서 비유 부분 추출
        analogy_section = ""
        if "[비유]" in theory_content:
            try:
                analogy_start = theory_content.index("[비유]")
                analogy_end = theory_content.index("[핵심 포인트]")
                analogy_section = theory_content[analogy_start:analogy_end]
            except ValueError:
                print(f"Warning: Could not extract analogy section for {topic}")

        # 실습 내용에서 예제 코드 추출
        practice_example = ""
        if "파일 작성" in practice_content:
            try:
                example_start = practice_content.index("파일 작성")
                example_end = practice_content.index("실행 단계")
                practice_example = practice_content[example_start:example_end]
            except ValueError:
                print(f"Warning: Could not extract practice example for {topic}")

        # 프롬프트 구성
        prompt = (
            f"다음 주제와 내용을 바탕으로 과제를 생성해주세요:\n\n"
            f"주제: {topic}\n\n"
            f"이론 내용의 비유:\n{analogy_section}\n\n"
            f"실습 예제:\n{practice_example}\n\n"
            f"요구사항:\n"
            f"1. 이론에서 사용된 비유를 활용하여 문제를 만들어주세요.\n"
            f"2. 실습에서 다룬 예제 코드를 확장하거나 응용하는 문제를 포함해주세요.\n"
            f"3. 실제 상황에서 적용할 수 있는 문제를 만들어주세요.\n\n"
            f"{prompt_template}"
        )

        return [{
            "role": "user",
            "content": prompt
        }] 

    async def analyze(self, submission: str) -> Dict[str, Any]:
        """과제 제출물 분석"""
        return {
            'answer_quality': self._analyze_answer_quality(submission),
            'understanding_level': self._analyze_understanding(submission),
            'feedback': self._generate_feedback(submission)
        }

    def _analyze_answer_quality(self, submission: str) -> str:
        """답안의 품질 분석"""
        # TODO: 실제 분석 로직 구현
        return "good"

    def _analyze_understanding(self, submission: str) -> str:
        """학습자의 이해도 분석"""
        # TODO: 실제 분석 로직 구현
        return "good"

    def _generate_feedback(self, submission: str) -> str:
        """피드백 생성"""
        # TODO: 실제 피드백 생성 로직 구현
        return "잘 작성되었습니다." 