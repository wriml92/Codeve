from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from .base_agent import BaseAgent
from courses.models import TheoryExplanation
import markdown2
import json
from asgiref.sync import sync_to_async
import os
from datetime import datetime
from courses.llm.theory_llm import TheoryLLM
from courses.file_manager import FileManager
from courses.db_manager import DatabaseManager

class TheoryAgent(BaseAgent):
    def __init__(self, llm: TheoryLLM):
        self.llm = llm
        self.file_manager = FileManager()
        self.db_manager = DatabaseManager()
    
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # 1. 이론 내용 생성
        theory_content = await self.llm.generate(data['topic'])
        
        # 2. 내용 분석
        analysis = await self.llm.analyze(theory_content)
        
        # 3. 파일 저장
        theory_path = await self.file_manager.save_theory(
            theory_content, 
            data['topic_id']
        )
        
        # 4. DB 저장
        theory_model = await self.db_manager.create_theory(
            content=theory_content,
            analysis=analysis,
            topic_id=data['topic_id']
        )
        
        return {
            'theory_id': theory_model.id,
            'file_path': theory_path,
            'analysis': analysis
        } 