from abc import ABC, abstractmethod
from typing import Dict, Any
import asyncio

class BaseAgent(ABC):
    def __init__(self, llm):
        self.llm = llm
    
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