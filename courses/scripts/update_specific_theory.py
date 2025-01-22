from courses.llm.theory_llm import TheoryLLM
import asyncio
from courses.models import TheoryContent

async def regenerate_theory(topic_id):
    print(f"Generating theory for {topic_id}...")
    llm = TheoryLLM()
    await llm.generate(topic_id)
    print(f"Completed {topic_id}")

# 변수, 문자열, 리스트 이론 재생성
topics = ['variables', 'strings', 'lists']
for topic in topics:
    asyncio.run(regenerate_theory(topic)) 