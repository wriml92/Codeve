from abc import ABC, abstractmethod
from typing import Dict, Any
from langchain_openai import ChatOpenAI

class BaseLLM(ABC):
    def __init__(self, model_name="gpt-4", temperature=0.7):
        self.llm = ChatOpenAI(
            model_name=model_name,
            temperature=temperature
        )
    
    @abstractmethod
    async def generate(self, prompt: str) -> str:
        pass

    @abstractmethod
    async def analyze(self, content: str) -> Dict[str, Any]:
        pass 