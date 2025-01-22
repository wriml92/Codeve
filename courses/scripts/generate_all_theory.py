from courses.llm.theory_llm import TheoryLLM
import asyncio

async def generate_all_theory():
    topics = [
        'input_output', 'variables', 'strings', 'lists', 'tuples',
        'dictionaries', 'conditionals', 'loops', 'functions',
        'classes', 'modules', 'exceptions', 'files'
    ]
    
    llm = TheoryLLM()
    for topic_id in topics:
        print(f"Generating theory for {topic_id}...")
        await llm.generate(topic_id)
        print(f"Completed {topic_id}")

# 모든 이론 생성 실행
asyncio.run(generate_all_theory()) 