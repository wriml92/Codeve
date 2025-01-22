from courses.llm.assignment_llm import AssignmentLLM
import asyncio
import json
from pathlib import Path

async def regenerate_assignment(topic_id):
    print(f"Generating assignments for {topic_id}...")
    llm = AssignmentLLM()
    assignment_data = await llm.generate_assignment(topic_id)
    base_dir = llm.data_dir
    assignment_file = base_dir / topic_id / 'content' / 'assignment.json'
    assignment_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(assignment_file, 'w', encoding='utf-8') as f:
        json.dump(assignment_data, f, ensure_ascii=False, indent=2)
    print(f"Completed {topic_id}")

# 문자열이랑 리스트 과제만 재생성
for topic in ['strings', 'lists']:
    asyncio.run(regenerate_assignment(topic)) 