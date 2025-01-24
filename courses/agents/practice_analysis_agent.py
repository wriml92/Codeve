from typing import Dict, Any
from .base_agent import BaseAgent
from anthropic import Anthropic
import os
from pathlib import Path
import json
from dotenv import load_dotenv
import base64
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

class PracticeAnalysisAgent(BaseAgent):
    def __init__(self):
        load_dotenv()
        api_key = os.getenv('ANTHROPIC_API_KEY')
        
        if api_key:
            api_key = api_key.strip().strip("'").strip('"').strip()
        else:
            raise ValueError("API 키가 설정되지 않았습니다.")
            
        self.anthropic = Anthropic(api_key=api_key)
        super().__init__(self.anthropic)
        self.data_dir = Path(__file__).parent.parent / 'data' / 'topics'
        self.prompt_template = self.load_prompt('practice_analysis_prompt.md')
        self.rate_limit_file = Path(__file__).parent / 'rate_limits.json'
        self.max_attempts = 3
        self.cooldown_minutes = 30

    def _check_rate_limit(self, user_id: str, topic_id: str) -> Dict[str, Any]:
        """사용자별 API 호출 제한 확인"""
        try:
            if not self.rate_limit_file.exists():
                return {'allowed': True, 'remaining_attempts': self.max_attempts}

            with open(self.rate_limit_file, 'r') as f:
                rate_limits = json.load(f)

            user_key = f"{user_id}_{topic_id}"
            user_limits = rate_limits.get(user_key, {
                'attempts': 0,
                'last_attempt': None,
                'cooldown_until': None
            })

            now = datetime.now()

            # 쿨다운 시간 확인
            if user_limits.get('cooldown_until'):
                cooldown_until = datetime.fromisoformat(user_limits['cooldown_until'])
                if now < cooldown_until:
                    remaining_minutes = int((cooldown_until - now).total_seconds() / 60)
                    return {
                        'allowed': False,
                        'error': f'분석 횟수 초과로 인한 대기 시간이 {remaining_minutes}분 남았습니다.'
                    }

            # 쿨다운이 끝났거나 없으면 시도 횟수 초기화
            if user_limits.get('cooldown_until'):
                cooldown_until = datetime.fromisoformat(user_limits['cooldown_until'])
                if now >= cooldown_until:
                    user_limits = {
                        'attempts': 0,
                        'last_attempt': None,
                        'cooldown_until': None
                    }

            remaining_attempts = self.max_attempts - user_limits['attempts']
            return {'allowed': remaining_attempts > 0, 'remaining_attempts': remaining_attempts}

        except Exception as e:
            print(f"rate limit 확인 중 오류 발생: {str(e)}")
            return {'allowed': True, 'remaining_attempts': self.max_attempts}

    def _update_rate_limit(self, user_id: str, topic_id: str):
        """사용자별 API 호출 횟수 업데이트"""
        try:
            rate_limits = {}
            if self.rate_limit_file.exists():
                with open(self.rate_limit_file, 'r') as f:
                    rate_limits = json.load(f)

            user_key = f"{user_id}_{topic_id}"
            user_limits = rate_limits.get(user_key, {
                'attempts': 0,
                'last_attempt': None,
                'cooldown_until': None
            })

            user_limits['attempts'] += 1
            user_limits['last_attempt'] = datetime.now().isoformat()

            # 최대 시도 횟수 도달 시 쿨다운 시간 설정
            if user_limits['attempts'] >= self.max_attempts:
                cooldown_until = datetime.now() + timedelta(minutes=self.cooldown_minutes)
                user_limits['cooldown_until'] = cooldown_until.isoformat()

            rate_limits[user_key] = user_limits

            with open(self.rate_limit_file, 'w') as f:
                json.dump(rate_limits, f, indent=2)

        except Exception as e:
            print(f"rate limit 업데이트 중 오류 발생: {str(e)}")

    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """에이전트의 주요 처리 로직"""
        topic_id = data.get('topic_id')
        image_path = data.get('image_path')
        user_id = data.get('user_id')  # user_id 추가 필요

        if not user_id:
            return {
                'success': False,
                'error': '사용자 ID가 제공되지 않았습니다.'
            }

        # rate limit 확인
        rate_limit_check = self._check_rate_limit(user_id, topic_id)
        if not rate_limit_check['allowed']:
            return {
                'success': False,
                'error': rate_limit_check.get('error', '분석 횟수가 초과되었습니다.')
            }

        # rate limit 업데이트
        self._update_rate_limit(user_id, topic_id)

        return await self.analyze_practice_image(topic_id, image_path)

    async def analyze_practice_image(self, topic_id: str, image_path: str) -> Dict[str, Any]:
        """실습 이미지 분석"""
        try:
            theory_content = self._load_theory_content(topic_id)
            practice_content = self._load_practice_content(topic_id)
            
            with open(image_path, 'rb') as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')

            messages = [{
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"""# 분석 대상
주제: {topic_id}

# 이론 내용
{theory_content}

# 실습 내용
{practice_content}

위 내용을 바탕으로 제출된 실습 이미지를 분석해주세요.
다음 항목들을 확인해주세요:

1. VSCode 환경 확인
   - VSCode 화면이 맞는지
   - 파이썬 파일이 올바른 이름으로 저장되었는지
   - 터미널이 열려있는지

2. 코드 내용 확인
   - 실습 예제와 일치하는지
   - 코드가 올바르게 작성되었는지
   - 주석이 포함되어 있는지

3. 실행 결과 확인
   - 터미널에 실행 명령어가 보이는지
   - 실행 결과가 예상 결과와 일치하는지

각 항목에 대해 통과 여부와 구체적인 피드백을 제공해주세요."""
                    },
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": image_data
                        }
                    }
                ]
            }]

            response = self.anthropic.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=1024,
                messages=messages
            )

            analysis_result = self._parse_analysis_response(response.content)
            
            self._save_analysis_result(topic_id, analysis_result)
            
            return analysis_result

        except Exception as e:
            import traceback
            print(f"이미지 분석 중 오류 발생: {str(e)}")
            print(traceback.format_exc())
            return {
                'success': False,
                'error': f'이미지 분석 중 오류 발생: {str(e)}'
            }

    def _load_theory_content(self, topic_id: str) -> str:
        """이론 내용 로드"""
        theory_file = self.data_dir / topic_id / 'content' / 'theory.html'
        if theory_file.exists():
            with open(theory_file, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f, 'html.parser')
                return soup.get_text()
        return ''

    def _load_practice_content(self, topic_id: str) -> str:
        """실습 내용 로드"""
        practice_file = self.data_dir / topic_id / 'content' / 'practice.html'
        try:
            if practice_file.exists():
                with open(practice_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # 메타데이터 추출 (필요한 경우)
                    soup = BeautifulSoup(content, 'html.parser')
                    # HTML 구조를 보존하면서 텍스트 추출
                    text_content = []
                    for section in soup.find_all('section'):
                        # 섹션 제목 추출
                        title = section.find(['h1', 'h2', 'h3'])
                        if title:
                            text_content.append(f"\n## {title.get_text().strip()}")
                        
                        # 내용 추출
                        for p in section.find_all(['p', 'li', 'pre']):
                            text = p.get_text().strip()
                            if text:
                                text_content.append(text)
                    
                    return '\n'.join(text_content)
            return ''
        except Exception as e:
            print(f"실습 내용 로드 중 오류 발생: {str(e)}")
            return ''

    def _parse_analysis_response(self, response: str) -> Dict[str, Any]:
        """Claude의 응답을 간결한 결과로 변환"""
        try:
            response_text = str(response)
            sections = {
                'vscode_env': self._extract_section_result(response_text, 'VSCode 환경'),
                'code_content': self._extract_section_result(response_text, '코드 내용'),
                'execution_result': self._extract_section_result(response_text, '실행 결과')
            }
            
            all_passed = all(section.get('passed', False) for section in sections.values())
            
            return {
                'success': True,
                'passed': all_passed,
                'feedback': self._generate_feedback(sections)
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'응답 파싱 중 오류 발생: {str(e)}'
            }

    def _extract_section_result(self, response: str, section_name: str) -> Dict[str, Any]:
        """응답에서 특정 섹션의 결과 추출"""
        try:
            section_start = response.find(section_name)
            if section_start == -1:
                return {
                    'passed': False,
                    'feedback': f'{section_name} 분석 결과를 찾을 수 없습니다.'
                }
            
            section_text = response[section_start:].split('\n\n')[0]
            
            positive_indicators = ['통과', '완료', '성공', '일치', '맞습니다', '좋습니다']
            passed = any(indicator in section_text for indicator in positive_indicators)
            
            return {
                'passed': passed,
                'feedback': section_text.strip()
            }
        except Exception as e:
            print(f"섹션 추출 중 오류: {str(e)}")
            return {
                'passed': False,
                'feedback': f'{section_name} 분석 중 오류 발생'
            }

    def _generate_feedback(self, sections: Dict[str, Any]) -> str:
        """간결한 피드백 생성"""
        feedback = []
        
        feedback.append("분석 결과")
        feedback.append("")
        
        # VSCode 환경
        feedback.append("1. VSCode 환경 확인:")
        vscode_items = [
            "VSCode 화면 캡처",
            "파일 이름 적합",
            "터미널 활성화 확인"
        ]
        for item in vscode_items:
            status = "통과" if sections['vscode_env']['passed'] else "미통과"
            feedback.append(f"\t• {item}: {status}")
        
        # 코드 내용
        feedback.append("2. 코드 내용 확인:")
        code_items = [
            "예제 코드 일치",
            "문법 적합성"
        ]
        for item in code_items:
            status = "통과" if sections['code_content']['passed'] else "미통과"
            feedback.append(f"\t• {item}: {status}")
        
        # 실행 결과
        feedback.append("3. 실행 결과 확인:")
        execution_items = [
            "실행 명령어",
            "결과 일치 여부"
        ]
        for item in execution_items:
            status = "통과" if sections['execution_result']['passed'] else "미통과"
            feedback.append(f"\t• {item}: {status}")
        
        # 추가 피드백 (주석 등 특별한 사항이 있을 경우)
        if "주석이 포함되어 있습니다" in str(sections['code_content']):
            feedback.append("\n주석을 잘 작성해주셨네요! 코드의 이해도가 높아 보입니다.")
        
        # 총평
        feedback.append("\n총평:")
        if all(section['passed'] for section in sections.values()):
            feedback.append("실습 지시사항을 정확히 따랐으며, 모든 항목이 통과되었습니다. 잘 수행하셨습니다! 앞으로도 꾸준한 연습으로 프로그래밍 실력을 더욱 향상시킬 수 있습니다.")
        else:
            feedback.append("일부 항목에서 개선이 필요합니다. 위의 피드백을 참고하여 수정해보세요.")
        
        return '\n'.join(feedback)

    def _save_analysis_result(self, topic_id: str, result: Dict[str, Any]) -> None:
        """분석 결과 저장

        저장된 분석 결과는 특정 주제 ID를 기준으로 파일 시스템의 "current/analysis" 디렉토리에 저장됩니다.
        파일 경로 구조는 `data/topics/<topic_id>/current/analysis/practice_analysis.json`입니다.
        이 함수는 디렉토리가 존재하지 않을 경우 생성하며, 결과를 JSON 파일로 저장합니다.
        """
        analysis_dir = self.data_dir / topic_id / 'current' / 'analysis'
        analysis_dir.mkdir(parents=True, exist_ok=True)
        
        analysis_file = analysis_dir / 'practice_analysis.json'
        with open(analysis_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False, sort_keys=True)
