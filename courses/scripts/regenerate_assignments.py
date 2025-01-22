import asyncio
from pathlib import Path
from courses.llm.assignment_llm import AssignmentLLM

async def regenerate_all_assignments():
    topics = [
        'input_output', 'variables', 'strings', 'lists', 'tuples',
        'dictionaries', 'conditionals', 'loops', 'functions',
        'classes', 'modules', 'exceptions', 'files'
    ]
    
    llm = AssignmentLLM()
    for topic_id in topics:
        print(f"Generating assignments for {topic_id}...")
        assignment_data = await llm.generate_assignment(topic_id)
        llm.save_assignment_data(topic_id, assignment_data)
        print(f"Completed {topic_id}")

if __name__ == "__main__":
    asyncio.run(regenerate_all_assignments()) 