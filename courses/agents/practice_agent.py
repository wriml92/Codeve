from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from .base_agent import BaseAgent
from courses.models import TheoryExplanation
from asgiref.sync import sync_to_async
import os
from courses.llm.practice_llm import PracticeLLM
from courses.utils.vscode_manager import VSCodeManager
from courses.utils.test_runner import TestRunner

class PracticeAgent(BaseAgent):
    def __init__(self, llm: PracticeLLM):
        self.llm = llm
        self.vscode_manager = VSCodeManager()
        self.test_runner = TestRunner()
    
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # 1. 실습 환경 준비
        practice_content = await self.llm.generate(data['theory_content'])
        
        # 2. VSCode 환경 설정
        vscode_env = await self.vscode_manager.setup_environment(
            practice_content,
            data['topic_id']
        )
        
        # 3. 테스트 케이스 준비
        test_cases = await self.test_runner.prepare_tests(practice_content)
        
        return {
            'vscode_config': vscode_env,
            'test_cases': test_cases,
            'practice_content': practice_content
        }
    
    async def evaluate_submission(self, submission: Dict[str, Any]) -> Dict[str, Any]:
        # 제출물 분석 및 피드백
        analysis = await self.llm.analyze(submission['code'])
        return analysis
    
