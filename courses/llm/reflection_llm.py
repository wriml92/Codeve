from .base_llm import BaseLLM

class ReflectionLLM(BaseLLM):
    def __init__(self, model_name="gpt-4", temperature=0.7):
        super().__init__(model_name, temperature)
        self.data_dir = self.base_dir / 'data' / 'topics'
        self.prompt_template = self.load_prompt('reflection_llm_prompt.md')

    async def generate(self, topic_id: str) -> str:
        """회고 내용 생성"""
        messages = [{
            "role": "user",
            "content": f"""# 입력 데이터
{{
    "topic": "{topic_id}"
}}

{self.prompt_template}"""
        }]
        
        response = await self.llm.agenerate([messages])
        return response.generations[0][0].text

    async def analyze(self, content: str):
        """회고 내용 분석"""
        # 구현 예정
        pass 