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