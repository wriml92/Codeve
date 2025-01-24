from abc import ABC, abstractmethod
from typing import Dict, Any
import asyncio
from pathlib import Path

class BaseAgent(ABC):
    def __init__(self, llm):
        self.llm = llm
        self.base_dir = Path(__file__).parent.parent
        self.prompt_dir = self.base_dir / 'agents' / 'agent_prompt'
    
    def load_prompt(self, filename: str) -> str:
        """프롬프트 템플릿 로드"""
        prompt_path = self.prompt_dir / filename
        if not prompt_path.exists():
            raise FileNotFoundError(f"프롬프트 파일을 찾을 수 없습니다: {filename}")
        
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    @abstractmethod
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """에이전트의 주요 처리 로직"""
        pass 

    async def execute_with_retry(self, func, *args, max_retries=3):
        for attempt in range(max_retries):
            try:
                return await func(*args)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                await asyncio.sleep(2 ** attempt)  # 지수 백오프 