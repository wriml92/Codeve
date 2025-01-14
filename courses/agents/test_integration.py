import os
from openai import OpenAI
from dotenv import load_dotenv
from courses.llm.theory_llm import TheoryLLM
from courses.llm.practice_llm import PracticeLLM
from courses.agents.theory_agent import TheoryAgent
from courses.agents.practice_agent import PracticeAgent

def test_openai_key():
    # 환경변수 로드
    load_dotenv()
    
    # API 키 존재 확인
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY가 설정되지 않았습니다.")
        return
        
    try:
        # OpenAI 클라이언트 초기화
        client = OpenAI()
        
        # 간단한 API 호출 테스트
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": "안녕하세요! 간단한 테스트입니다."}
            ]
        )
        
        # 응답 확인
        print("\n=== OpenAI API 테스트 결과 ===")
        print("✅ API 연결 성공!")
        print("\n[응답 내용]")
        print(response.choices[0].message.content)
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {str(e)}")
        
    print("\n=== 테스트 완료 ===")

class TestIntegration:
    def test_theory_flow(self):
        """이론 학습 흐름 테스트"""
        theory_llm = TheoryLLM()
        theory_agent = TheoryAgent(theory_llm)
        
        # 테스트 케이스 실행
        result = theory_agent.process({
            'topic_id': 'python_variables',
            'topic': '파이썬 변수'
        })
        
        assert result['theory_id'] is not None
        assert os.path.exists(result['file_path'])

    def test_practice_flow(self):
        """실습 흐름 테스트"""
        practice_llm = PracticeLLM() 
        practice_agent = PracticeAgent(practice_llm)
        
        # 테스트 케이스 실행
        result = practice_agent.process({
            'topic_id': 'python_variables',
            'theory_content': '변수 이론 내용...'
        })
        
        assert result['vscode_config'] is not None
        assert len(result['test_cases']) > 0

if __name__ == "__main__":
    test_openai_key() 