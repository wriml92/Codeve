from typing import Dict, Any, List
import json
from pathlib import Path
import ast
import io
import sys
from contextlib import redirect_stdout

class AnalysisAgent:
    def __init__(self):
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

    async def analyze(self, assignment_type: str, answer: str, assignment_id: int, topic_id: str) -> Dict[str, Any]:
        """과제 답안 분석"""
        try:
            # 과제 데이터 로드
            assignment_data = self._load_assignment_data(topic_id)
            assignment = next((a for a in assignment_data['assignments'] if a['id'] == assignment_id), None)
            
            if not assignment:
                return {'correct': False, 'message': '과제를 찾을 수 없습니다.'}
            
            if assignment_type in ['concept', 'theory_concept', 'metaphor']:
                # 객관식 문제 채점
                correct_answer = assignment.get('correct_answer')
                if answer == correct_answer:
                    return {
                        'correct': True,
                        'message': '정답입니다! ' + assignment.get('hint', '')
                    }
                return {
                    'correct': False,
                    'message': '틀렸습니다. ' + assignment.get('hint', '')
                }
                
            elif assignment_type in ['implementation_basic', 'implementation_advanced']:
                # 코드 구현 문제 채점
                test_cases = assignment.get('test_cases', [])
                test_results = []
                all_passed = True
                
                for test_case in test_cases:
                    # 테스트 케이스 실행...
                    passed = self._run_test(answer, test_case)
                    test_results.append({
                        'case': f"입력: {test_case['input']} → 출력: {test_case['output']}",
                        'passed': passed
                    })
                    if not passed:
                        all_passed = False
                
                return {
                    'correct': all_passed,
                    'message': '모든 테스트를 통과했습니다!' if all_passed else '일부 테스트가 실패했습니다.',
                    'test_results': test_results
                }
            
            return {'correct': False, 'message': '지원하지 않는 과제 유형입니다.'}
            
        except Exception as e:
            return {'correct': False, 'message': f'채점 중 오류가 발생했습니다: {str(e)}'}

    def _load_assignment_data(self, topic_id: str) -> Dict:
        """토픽의 과제 데이터 로드"""
        base_dir = Path(__file__).parent.parent
        assignment_path = base_dir / 'data' / 'topics' / topic_id / 'content' / 'assignment.json'
        
        with open(assignment_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _analyze_concept(self, answer: str, assignment: Dict) -> Dict[str, Any]:
        """개념 이해 문제 분석"""
        correct_answer = str(assignment['correct_answer'])  # 정답은 선택지 번호 (1, 2, 3, 4)
        hint = assignment.get('hint', '다시 한번 생각해보세요.')
        
        is_correct = answer == correct_answer
        
        return {
            'correct': is_correct,
            'message': '정답입니다! 다음 문제로 넘어가세요.' if is_correct else f'틀렸습니다. 힌트: {hint}',
            'score': 100 if is_correct else 0
        }

    def _analyze_code_analysis(self, answer: str, assignment: Dict) -> Dict[str, Any]:
        """코드 분석 문제 분석"""
        expected_points = assignment.get('analysis_points', [])
        hint = assignment.get('hint', '코드의 실행 흐름을 다시 한번 살펴보세요.')
        
        # 답안에서 핵심 포인트들이 언급되었는지 확인
        score = 0
        missing_points = []
        
        for point in expected_points:
            if point.lower() in answer.lower():
                score += 100 / len(expected_points)
            else:
                missing_points.append(point)
        
        is_correct = score >= 80
        message = '정답입니다! 다음 문제로 넘어가세요.' if is_correct else \
                 f'틀렸습니다. 다음 내용을 고려해보세요: {", ".join(missing_points)}'
        
        return {
            'correct': is_correct,
            'message': message,
            'score': score
        }

    def _analyze_implementation(self, answer: str, assignment: Dict) -> Dict[str, Any]:
        """코드 구현 문제 분석"""
        test_cases = assignment.get('test_cases', [])
        hint = assignment.get('hint', '테스트 케이스를 만족하도록 코드를 수정해보세요.')
        
        try:
            # 코드 실행 및 테스트
            results = self._run_test_cases(answer, test_cases)
            passed_tests = sum(1 for r in results if r['passed'])
            score = (passed_tests / len(test_cases)) * 100
            
            is_correct = score >= 80
            
            if is_correct:
                message = '정답입니다! 모든 테스트 케이스를 통과했습니다.'
            else:
                failed_cases = [r['case'] for r in results if not r['passed']]
                message = f'틀렸습니다. 다음 테스트 케이스를 확인해보세요: {", ".join(failed_cases)}\n힌트: {hint}'
            
            return {
                'correct': is_correct,
                'message': message,
                'score': score,
                'test_results': results
            }
            
        except Exception as e:
            return {
                'correct': False,
                'message': f'코드 실행 중 오류가 발생했습니다: {str(e)}',
                'score': 0,
                'test_results': []
            }

    def _run_test_cases(self, code: str, test_cases: List[Dict]) -> List[Dict]:
        """테스트 케이스 실행"""
        results = []
        
        # 안전한 실행을 위한 로컬 네임스페이스
        local_dict = {}
        
        try:
            # 사용자 코드 실행
            exec(code, {'__builtins__': __builtins__}, local_dict)
            
            # 각 테스트 케이스 실행
            for test_case in test_cases:
                input_value = test_case['input']
                expected_output = test_case['output']
                
                # 입력값 설정
                sys.stdin = io.StringIO(input_value)
                output = io.StringIO()
                
                # 코드 실행 및 출력 캡처
                with redirect_stdout(output):
                    exec(code, {'__builtins__': __builtins__}, local_dict)
                
                actual_output = output.getvalue().strip()
                passed = actual_output == str(expected_output).strip()
                
                results.append({
                    'case': f'입력: {input_value}, 기대 출력: {expected_output}',
                    'passed': passed,
                    'actual_output': actual_output
                })
                
        except Exception as e:
            results.append({
                'case': '코드 실행',
                'passed': False,
                'error': str(e)
            })
        
        finally:
            # 표준 입출력 복구
            sys.stdin = sys.__stdin__
        
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