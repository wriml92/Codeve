from typing import Dict, Any
from .base_agent import BaseAgent

class AnalysisAgent(BaseAgent):
    def __init__(self, threshold: float = 80.0):
        self.threshold = threshold  # 기준점 (기본값 80%)

    async def process(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """사용자 학습 데이터를 분석하고 성취도를 계산"""
        scores = user_data.get('scores', [])
        achievement_rate = self.calculate_achievement_rate(scores)

        # 기준 판별
        is_meeting_criteria = self.check_criteria(achievement_rate)

        return {
            'achievement_rate': achievement_rate,
            'meets_criteria': is_meeting_criteria
        }

    def calculate_achievement_rate(self, scores: list) -> float:
        """학습 성취도 계산"""
        if not scores:
            return 0.0
        return sum(scores) / len(scores)

    def check_criteria(self, achievement_rate: float) -> bool:
        """기준 판별"""
        return achievement_rate >= self.threshold 