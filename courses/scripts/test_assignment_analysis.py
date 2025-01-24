import os
import sys
import django
import asyncio
from pathlib import Path

# Django 설정을 위한 프로젝트 루트 경로 추가
project_root = str(Path(__file__).parent.parent.parent)
sys.path.append(project_root)

# Django 설정 초기화
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Codeve.settings')
django.setup()

from courses.agents.assignment_analysis_agent import AssignmentAnalysisAgent

# 테스트할 토픽과 과제 목록
TEST_ASSIGNMENTS = [
    {
        'topic_id': 'input_output',
        'assignments': [
            {
                'id': 1,
                'type': 'concept',
                'answer': '2',  # 예시 답안
                'expected': True  # 예상 결과 (정답 여부)
            },
            {
                'id': 2,
                'type': 'implementation_basic',
                'answer': '''# 사용자로부터 이름을 입력받습니다
name = input("이름을 입력해주세요: ")
print("안녕하세요, " + name + "님! 👋")''',
                'expected': True
            }
        ]
    },
    {
        'topic_id': 'variables',
        'assignments': [
            {
                'id': 1,
                'type': 'concept',
                'answer': '1',
                'expected': True
            },
            {
                'id': 2,
                'type': 'implementation_basic',
                'answer': '''# 숫자를 변수에 저장합니다
number = 42
# 숫자를 100만큼 증가시킵니다
result = number + 100
print(f"결과는 {result}입니다! 🎯")''',
                'expected': True
            }
        ]
    }
]

async def test_assignment_analysis():
    """과제 분석 테스트 실행"""
    print("과제 분석 테스트를 시작합니다...")
    
    agent = AssignmentAnalysisAgent()
    total_tests = 0
    passed_tests = 0
    
    for topic in TEST_ASSIGNMENTS:
        print(f"\n=== {topic['topic_id']} 과제 테스트 ===")
        
        for assignment in topic['assignments']:
            total_tests += 1
            try:
                print(f"\n[테스트 {total_tests}] {assignment['type']} 유형 과제 분석")
                
                result = await agent.analyze(
                    assignment_type=assignment['type'],
                    answer=assignment['answer'],
                    assignment_id=assignment['id'],
                    topic_id=topic['topic_id']
                )
                
                is_correct = result.get('correct', False)
                if is_correct == assignment['expected']:
                    passed_tests += 1
                    print(f"✅ 테스트 통과")
                    print(f"피드백: {result.get('message', '')}")
                else:
                    print(f"❌ 테스트 실패")
                    print(f"기대 결과: {assignment['expected']}")
                    print(f"실제 결과: {is_correct}")
                    print(f"피드백: {result.get('message', '')}")
                
            except Exception as e:
                print(f"❌ 테스트 중 오류 발생: {str(e)}")
    
    # 테스트 결과 요약
    print(f"\n=== 테스트 결과 요약 ===")
    print(f"총 테스트: {total_tests}")
    print(f"통과: {passed_tests}")
    print(f"실패: {total_tests - passed_tests}")
    print(f"성공률: {(passed_tests/total_tests)*100:.1f}%")

async def main():
    """메인 실행 함수"""
    await test_assignment_analysis()

if __name__ == '__main__':
    # 비동기 실행
    asyncio.run(main()) 