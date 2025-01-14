class CourseStateManager:
    def __init__(self, user_id: str, course_id: str):
        self.user_id = user_id
        self.course_id = course_id
        
    async def update_progress(self, topic_id: str, status: str):
        """학습 진행 상태 업데이트"""
        pass
        
    async def get_next_topic(self) -> Dict:
        """다음 학습할 토픽 반환"""
        pass
        
    async def get_learning_path(self) -> List[Dict]:
        """사용자의 학습 경로 생성"""
        pass
