from abc import ABC, abstractmethod
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from pathlib import Path
import json
import os
from dotenv import load_dotenv

class BaseLLM(ABC):
    def __init__(self, model_name="gpt-4", temperature=0.7):
        load_dotenv()
        self.llm = ChatOpenAI(
            model_name=model_name,
            temperature=temperature
        )
        self.base_dir = Path(__file__).parent.parent
        self.data_dir = self.base_dir / 'data'
        self.prompt_dir = self.base_dir / 'llm' / 'prompts'
        
    async def generate_completion(self, prompt: str) -> str:
        """LLM을 사용하여 텍스트 생성"""
        try:
            response = await self.llm.ainvoke(prompt)
            return response.content
        except Exception as e:
            print(f"Error in generate_completion: {e}")
            return ""

    def load_prompt(self, filename: str) -> str:
        """프롬프트 템플릿 로드"""
        prompt_path = self.base_dir / 'llm' / 'prompts' / filename
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
            
    def save_data(self, data: Dict, file_path: Path) -> None:
        """데이터 저장"""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
    def load_data(self, file_path: Path) -> Dict:
        """데이터 로드"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    @abstractmethod
    async def generate(self, topic: str) -> str:
        """콘텐츠 생성"""
        pass

    @abstractmethod
    async def analyze(self, content: str) -> Dict[str, Any]:
        """콘텐츠 분석"""
        pass 