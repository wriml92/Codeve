'과제 분석 에이전트'
from typing import Dict, Any, List
import json
from pathlib import Path
import ast
import io
import sys
from contextlib import redirect_stdout
import re
import random
from .base_agent import BaseAgent
from anthropic import Anthropic
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

class AssignmentAnalysisAgent(BaseAgent):
    def __init__(self):
        load_dotenv()
        api_key = os.getenv('ANTHROPIC_API_KEY')
        
        if not api_key:
            raise ValueError("API 키가 설정되지 않았습니다.")
            
        api_key = api_key.strip().strip("'").strip('"').strip()
        self.anthropic = Anthropic(api_key=api_key)
        super().__init__()
        self.prompt_template = self.load_prompt('assignment_analysis_prompt.md')
        self.attempts_file = Path(__file__).parent / 'assignment_attempts.json'
        self.max_attempts = 3  # 문제당 최대 시도 횟수
        self.cooldown_minutes = 30  # 초과 시 대기 시간
        self.data_dir = Path(__file__).parent.parent / 'data' / 'topics'
        self.score_weights = {
            'concept': 0.3,
            'analysis': 0.3,
            'implementation': 0.4
        }
        self.attempt_penalties = {
            1: 1.0,  # 첫 시도
            2: 0.9,  # 두 번째
            3: 0.8,  # 세 번째
            4: 0.7   # 네 번째 이상
        }
        self.thresholds = {
            'proceed': 80.0,
            'weak_point': 60.0,
            'critical': 40.0
        }
        # 피드백 스타일 설정
        self.feedback_style = {
            "positive_reinforcement": True,
            "creativity_praise": True,
            "encouragement_messages": [
                "멋진 시도예요! 🌟",
                "창의적인 접근이네요! ✨",
                "자기만의 스타일로 잘 표현했어요! 💫",
                "예제와 다르지만 훌륭한 해결방법이에요! 🎯",
                "코드가 잘 작동하네요! 👏",
                "이런 방식으로 생각하다니 대단해요! 🚀"
            ],
            "improvement_suggestions": [
                "조금 더 발전시켜볼까요? 💪",
                "이렇게 해보는 건 어떨까요? 💡",
                "다음 단계로 도전해보세요! 🎯",
                "새로운 시도를 해보는 건 어떨까요? ✨"
            ]
        }

    def _check_attempt_limit(self, user_id: str, topic_id: str, assignment_id: int) -> Dict[str, Any]:
        """사용자별 과제 제출 횟수 제한 확인"""
        try:
            if not self.attempts_file.exists():
                return {'allowed': True, 'remaining_attempts': self.max_attempts}

            with open(self.attempts_file, 'r') as f:
                attempts = json.load(f)

            attempt_key = f"{user_id}_{topic_id}_{assignment_id}"
            user_attempts = attempts.get(attempt_key, {
                'attempts': 0,
                'last_attempt': None,
                'cooldown_until': None
            })

            now = datetime.now()

            # 쿨다운 시간 확인
            if user_attempts.get('cooldown_until'):
                cooldown_until = datetime.fromisoformat(user_attempts['cooldown_until'])
                if now < cooldown_until:
                    remaining_minutes = int((cooldown_until - now).total_seconds() / 60)
                    return {
                        'allowed': False,
                        'error': f'제출 횟수 초과로 인한 대기 시간이 {remaining_minutes}분 남았습니다.'
                    }

            # 쿨다운이 끝났거나 없으면 시도 횟수 초기화
            if user_attempts.get('cooldown_until'):
                cooldown_until = datetime.fromisoformat(user_attempts['cooldown_until'])
                if now >= cooldown_until:
                    user_attempts = {
                        'attempts': 0,
                        'last_attempt': None,
                        'cooldown_until': None
                    }

            remaining_attempts = self.max_attempts - user_attempts['attempts']
            return {'allowed': remaining_attempts > 0, 'remaining_attempts': remaining_attempts}

        except Exception as e:
            print(f"제출 횟수 확인 중 오류 발생: {str(e)}")
            return {'allowed': True, 'remaining_attempts': self.max_attempts}

    def _update_attempt_count(self, user_id: str, topic_id: str, assignment_id: int):
        """사용자별 과제 제출 횟수 업데이트"""
        try:
            attempts = {}
            if self.attempts_file.exists():
                with open(self.attempts_file, 'r') as f:
                    attempts = json.load(f)

            attempt_key = f"{user_id}_{topic_id}_{assignment_id}"
            user_attempts = attempts.get(attempt_key, {
                'attempts': 0,
                'last_attempt': None,
                'cooldown_until': None
            })

            user_attempts['attempts'] += 1
            user_attempts['last_attempt'] = datetime.now().isoformat()

            # 최대 시도 횟수 도달 시 쿨다운 시간 설정
            if user_attempts['attempts'] >= self.max_attempts:
                cooldown_until = datetime.now() + timedelta(minutes=self.cooldown_minutes)
                user_attempts['cooldown_until'] = cooldown_until.isoformat()

            attempts[attempt_key] = user_attempts

            with open(self.attempts_file, 'w') as f:
                json.dump(attempts, f, indent=2)

        except Exception as e:
            print(f"제출 횟수 업데이트 중 오류 발생: {str(e)}")

    async def analyze(self, assignment_type: str, answer: str, assignment_id: int, topic_id: str, user_id: str) -> Dict[str, Any]:
        """과제 답안 분석"""
        try:
            # 파라미터 검증
            if not all([assignment_type, answer, assignment_id, topic_id, user_id]):
                missing_params = []
                if not assignment_type: missing_params.append('assignment_type')
                if not answer: missing_params.append('answer')
                if not assignment_id: missing_params.append('assignment_id')
                if not topic_id: missing_params.append('topic_id')
                if not user_id: missing_params.append('user_id')
                return {
                    'correct': False,
                    'message': f'필수 파라미터가 누락되었습니다: {", ".join(missing_params)}'
                }

            # assignment_id를 정수로 변환
            try:
                assignment_id = int(assignment_id)
            except (TypeError, ValueError):
                return {
                    'correct': False,
                    'message': 'assignment_id는 정수여야 합니다.'
                }

            # 제출 횟수 제한 확인
            attempt_check = self._check_attempt_limit(user_id, topic_id, assignment_id)
            if not attempt_check['allowed']:
                return {
                    'correct': False,
                    'message': attempt_check['error']
                }

            # 과제 데이터 로드
            assignment_data = self._load_assignment_data(topic_id)
            assignment = next((a for a in assignment_data['assignments'] if a['id'] == assignment_id), None)
            
            if not assignment:
                return {'correct': False, 'message': '과제를 찾을 수 없습니다.'}

            # LLM을 사용한 답안 분석
            analysis_result = await self._analyze_with_llm(assignment_type, answer, assignment)
            
            # 제출 횟수 업데이트
            self._update_attempt_count(user_id, topic_id, assignment_id)
            
            # 남은 시도 횟수 추가
            attempt_check = self._check_attempt_limit(user_id, topic_id, assignment_id)
            analysis_result['remaining_attempts'] = attempt_check.get('remaining_attempts', 0)
            
            return analysis_result

        except Exception as e:
            return {'correct': False, 'message': f'채점 중 오류가 발생했습니다: {str(e)}'}

    async def _analyze_with_llm(self, assignment_type: str, answer: str, assignment: Dict) -> Dict[str, Any]:
        """LLM을 사용한 답안 분석"""
        try:
            if assignment_type in ['concept_basic', 'concept_application', 'concept_analysis', 'concept_debug', 'metaphor', 'theory_concept', 'concept_synthesis']:
                prompt = f"""# 과제 정보
문제 유형: {assignment_type}
문제 내용: {assignment['content']}
제출한 답안: {answer}
정답: {assignment['correct_answer']}

위 정보를 바탕으로 다음을 분석해주세요:
1. 답안이 정답인가요?
2. 답안에 대한 구체적인 피드백을 제공해주세요.
3. 학습자의 이해도를 평가해주세요.
4. 추가 학습이 필요한 부분이 있다면 제안해주세요."""

            elif assignment_type in ['implementation_playground', 'implementation_modify', 'implementation_creative']:
                test_cases_str = "\n".join([
                    f"입력: {tc['input']}, 예상 출력: {tc['output']}"
                    for tc in assignment['test_cases']
                ])
                
                prompt = f"""# 과제 정보
문제 유형: {assignment_type}
문제 내용: {assignment['content']}
테스트 케이스:
{test_cases_str}

제출한 코드:
{answer}

위 정보를 바탕으로 다음을 분석해주세요:
1. 코드가 문제의 요구사항을 충족하나요?
2. 코드의 구현 방식과 스타일은 적절한가요?
3. 개선이 필요한 부분이 있다면 무엇인가요?
4. 학습자의 코딩 스킬 수준을 평가해주세요."""

            response = await self.anthropic.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=1024,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            # LLM 응답 파싱
            analysis = str(response.content)
            
            # 객관식 문제의 경우 정답 여부 직접 비교
            if assignment_type in ['concept_basic', 'concept_application', 'concept_analysis', 'concept_debug', 'metaphor', 'theory_concept', 'concept_synthesis']:
                is_correct = answer == assignment['correct_answer']
            else:
                # 구현 문제의 경우 테스트 케이스 실행
                test_results = self._run_test_cases(answer, assignment['test_cases'])
                is_correct = all(result['passed'] for result in test_results)

            # 긍정적인 피드백 선택
            encouragement = random.choice(self.feedback_style['encouragement_messages'])
            improvement = random.choice(self.feedback_style['improvement_suggestions'])

            return {
                'correct': is_correct,
                'message': analysis,
                'feedback': f"{encouragement}\n\n{analysis}\n\n{improvement if not is_correct else ''}",
                'test_results': test_results if assignment_type in ['implementation_playground', 'implementation_modify', 'implementation_creative'] else None
            }

        except Exception as e:
            return {
                'correct': False,
                'message': f'답안 분석 중 오류가 발생했습니다: {str(e)}'
            }

    def _load_assignment_data(self, topic_id: str) -> Dict[str, Any]:
        """과제 데이터 로드"""
        try:
            answer_file = self.data_dir / topic_id / 'content' / 'assignment_answers.json'
            if not answer_file.exists():
                raise FileNotFoundError(f'과제 정답 파일을 찾을 수 없습니다: {answer_file}')

            with open(answer_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise Exception(f'과제 데이터 로드 중 오류 발생: {str(e)}')

    def _run_test_cases(self, code: str, test_cases: List[Dict]) -> List[Dict]:
        """구현 문제의 테스트 케이스 실행"""
        results = []
        
        # 안전한 실행을 위한 전역 변수 설정
        globals_dict = {
            '__builtins__': {
                'print': print,
                'len': len,
                'range': range,
                'int': int,
                'str': str,
                'float': float,
                'list': list,
                'dict': dict,
                'set': set,
                'tuple': tuple,
                'sum': sum,
                'min': min,
                'max': max,
                'abs': abs,
                'round': round
            }
        }
        
        try:
            # 코드 컴파일 및 실행
            code_obj = compile(code, '<string>', 'exec')
            
            for test_case in test_cases:
                try:
                    # 각 테스트 케이스마다 새로운 로컬 스코프 생성
                    locals_dict = {}
                    
                    # 입력값 설정
                    if isinstance(test_case['input'], list):
                        for i, value in enumerate(test_case['input']):
                            locals_dict[f'input_{i+1}'] = value
                    else:
                        locals_dict['input_value'] = test_case['input']
                    
                    # 출력 캡처를 위한 StringIO 객체
                    output = io.StringIO()
                    
                    # 코드 실행 및 출력 캡처
                    with redirect_stdout(output):
                        exec(code_obj, globals_dict, locals_dict)
                    
                    # 실제 출력값 가져오기
                    actual_output = output.getvalue().strip()
                    
                    # 예상 출력값과 비교
                    expected_output = str(test_case['output']).strip()
                    passed = actual_output == expected_output
                    
                    results.append({
                        'test_case': test_case,
                        'passed': passed,
                        'actual_output': actual_output,
                        'expected_output': expected_output
                    })
                    
                except Exception as e:
                    results.append({
                        'test_case': test_case,
                        'passed': False,
                        'error': str(e)
                    })
                    
        except SyntaxError as e:
            return [{
                'passed': False,
                'error': f'코드에 문법 오류가 있습니다: {str(e)}'
            }]
        except Exception as e:
            return [{
                'passed': False,
                'error': f'코드 실행 중 오류가 발생했습니다: {str(e)}'
            }]
            
        return results

    def _calculate_scores(self, questions):
        # 점수 계산 로직
        pass

    def _identify_weak_points(self, scores):
        # 취약점 식별 로직
        pass

    def _generate_recommendations(self, scores):
        # 추천사항 생성 로직
        pass

    def _calculate_total_score(self, scores):
        # 종합 점수 계산 로직
        pass

    def _calculate_achievement_rate(self, scores: list) -> float:
        """학습 성취도 계산"""
        if not scores:
            return 0.0
        return sum(scores) / len(scores)

    def check_criteria(self, achievement_rate: float) -> bool:
        """기준 판별"""
        return achievement_rate >= self.thresholds['proceed']

    def _analyze_code_quality(self, code: str) -> Dict[str, Any]:
        """코드 품질 분석"""
        try:
            quality_analysis = {
                'has_comments': bool(re.search(r'#.*', code)),
                'code_length': len(code.splitlines()),
                'creativity': bool(re.search(r'[^!]\s*[😊🌟✨💫🎯👋]', code))  # 창의적 표현 확인
            }
            return quality_analysis
        except Exception as e:
            print(f"코드 품질 분석 중 오류: {str(e)}")
            return {}

    def _analyze_execution_result(self, code: str) -> Dict[str, Any]:
        """코드 실행 결과 분석"""
        try:
            # 안전한 환경에서 코드 실행
            local_vars = {}
            exec(code, {"__builtins__": {}}, local_vars)
            return {
                'success': True,
                'output': str(local_vars.get('__output__', '실행 결과 없음'))
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _generate_feedback(self, quality: Dict, exec_result: Dict) -> str:
        """분석 결과를 바탕으로 긍정적이고 격려하는 피드백 생성"""
        feedback = []
        
        # 실행 성공 여부에 따른 기본 피드백
        if exec_result.get('success'):
            feedback.append(random.choice(self.feedback_style['encouragement_messages']))
            
            # 창의성 칭찬
            if quality.get('creativity') and self.feedback_style['creativity_praise']:
                feedback.append("✨ 자기만의 독특한 표현을 넣어서 더욱 멋진 코드가 되었네요!")
        else:
            feedback.append(f"💪 거의 다 왔어요! 다음 부분만 수정해보면 될 것 같아요: {exec_result.get('error')}")

        # 코드 품질에 대한 긍정적 피드백
        if quality.get('has_comments'):
            feedback.append("📝 주석을 잘 작성해주셨네요! 코드를 이해하기 쉽게 설명해주셨어요.")
        else:
            feedback.append("💡 코드가 잘 작성되었어요! 주석을 추가하면 더 멋진 코드가 될 것 같아요.")
        
        # 코드 길이에 따른 피드백
        if quality.get('code_length', 0) > 5:
            feedback.append("🚀 코드를 확장해서 작성하셨네요! 새로운 시도를 해보시는 모습이 멋져요.")
        
        # 개선 제안
        if not exec_result.get('success') or not quality.get('has_comments'):
            feedback.append(random.choice(self.feedback_style['improvement_suggestions']))
        
        # 마무리 격려 메시지
        feedback.append("\n💫 계속해서 이렇게 자신만의 방식으로 코드를 작성해보세요! 여러분의 창의성이 빛나고 있어요.")
        
        return "\n".join(feedback) 