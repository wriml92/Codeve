from typing import List, Dict
import json
import asyncio
import argparse
from langchain_openai import ChatOpenAI
from theory_agent import TheoryAgent
import os
from dotenv import load_dotenv

async def process_topics(topics: List[Dict], start_from: int = None, end_at: int = None) -> None:
    """선택된 토픽들에 대해 TheoryAgent 실행"""
    load_dotenv()
    
    llm = ChatOpenAI(
        temperature=0.7,
        model="gpt-4-turbo-preview"
    )
    
    agent = TheoryAgent(llm)
    
    # 처리할 토픽 필터링
    selected_topics = topics[start_from-1:end_at] if start_from else topics
    
    for topic in selected_topics:
        print(f"\n=== 처리 중: {topic['name']} (order: {topic['order']}) ===")
        try:
            result = await agent.process(topic)
            
            if result['success']:
                output_dir = os.path.join('courses', 'theories')
                os.makedirs(output_dir, exist_ok=True)
                
                file_path = os.path.join(output_dir, f"{topic['id']}.md")
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(result['explanation'])
                
                print(f"✅ {topic['name']} 처리 완료")
                print(f"   파일 저장됨: {file_path}")
                
        except Exception as e:
            print(f"❌ {topic['name']} 처리 실패: {str(e)}")
            
        # API 호출 제한을 위한 딜레이
        await asyncio.sleep(1)

async def main():
    # 커맨드 라인 인자 파싱
    parser = argparse.ArgumentParser(description='특정 코스의 이론 문서를 생성합니다.')
    parser.add_argument('--course', type=str, default='python', help='처리할 코스 ID (기본값: python)')
    parser.add_argument('--start', type=int, help='시작할 토픽 순서 (1부터 시작)')
    parser.add_argument('--end', type=int, help='마지막 토픽 순서')
    args = parser.parse_args()

    # course_list.json 읽기
    with open('courses/agents/course_list.json', 'r', encoding='utf-8') as f:
        course_data = json.load(f)
    
    if args.course not in course_data:
        print(f"❌ 오류: '{args.course}' 코스를 찾을 수 없습니다.")
        print(f"사용 가능한 코스: {', '.join(course_data.keys())}")
        return
    
    topics = course_data[args.course]['topics']
    
    # 입력값 검증
    if args.start and (args.start < 1 or args.start > len(topics)):
        print(f"❌ 오류: 시작 순서는 1에서 {len(topics)} 사이여야 합니다.")
        return
        
    if args.end and (args.end < args.start or args.end > len(topics)):
        print(f"❌ 오류: 종료 순서는 시작 순서보다 크고 {len(topics)} 이하여야 합니다.")
        return

    print(f"\n=== {course_data[args.course]['name']} 코스 처리 시작 ===")
    if args.start or args.end:
        print(f"토픽 범위: {args.start or 1} ~ {args.end or len(topics)}")
    
    await process_topics(topics, args.start, args.end)

if __name__ == "__main__":
    asyncio.run(main()) 