"""
교육 콘텐츠 생성 도구

이 스크립트는 Python 교육 플랫폼의 다양한 교육 콘텐츠를 생성하는 도구입니다.
GPT-4를 활용하여 이론, 실습, 과제 등의 콘텐츠를 자동으로 생성합니다.

생성 가능한 콘텐츠:
1. 이론 학습 자료
   - 개념 설명
   - 예제 코드
   - 실행 결과
   - 추가 참고 자료

2. 실습 가이드
   - 단계별 실습 지침
   - 예상 결과
   - 문제 해결 팁
   - 자주 하는 실수

3. 과제 문제
   - 객관식 문제
   - 코드 분석 문제
   - 구현 문제
   - 응용 문제

저장 형식:
- 이론: HTML 형식
- 실습: JSON 형식
- 과제: JSON 형식

사용 방법:
1. 이론 콘텐츠 생성:
   python content_generator.py theory <topic_id>

2. 실습 가이드 생성:
   python content_generator.py practice <topic_id>

3. 과제 생성:
   python content_generator.py assignment <topic_id>

주의사항:
- OpenAI API 키 필요
- 생성된 콘텐츠는 검토 후 사용 권장
- 대규모 생성 시 API 비용 고려 필요
"""

from pathlib import Path
import json

class ContentGenerator:
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        # course_list.json 경로 수정
        self.course_list_path = self.base_dir / 'data' / 'course_list.json'
        self.data_dir = self.base_dir / 'data' / 'topics'

    async def generate_topic(self, topic_id: str, content_type: str = 'all', force: bool = False):
        """특정 토픽의 콘텐츠 생성"""
        # course_list.json 로드
        with open(self.course_list_path, 'r', encoding='utf-8') as f:
            course_list = json.load(f)
            
        # ... 나머지 코드 ... 