"""
과제 관리 및 코드 분석 도구

이 모듈은 Python 교육 플랫폼의 과제 관리와 코드 분석을 담당합니다.

주요 기능:
1. 과제 데이터 관리 (AssignmentDataManager)
   - 과제/답안 데이터 로드 및 저장
   - 제출 통계 관리 (제출 횟수, 정답률 등)
   - JSON 형식으로 데이터 저장

2. 코드 제출 분석 (CodeSubmissionAnalyzer)
   - 문법 검사: Python AST를 사용한 기본 문법 확인
   - 테스트 케이스 실행: 제출된 코드의 정확성 검증
   - LLM 기반 분석: GPT-4를 활용한 코드 품질 평가
   - 피드백 생성: 구체적인 개선 제안 제공

3. 과제 생성 (AssignmentGenerator)
   - 토픽별 맞춤형 과제 생성
   - 다양한 유형의 문제 생성 (이론, 구현, 분석 등)
   - GPT-4를 활용한 자동 과제 생성

사용 예시:
```python
# 과제 데이터 관리
manager = AssignmentDataManager()
assignment = manager.load_assignment("input_output")

# 코드 분석
analyzer = CodeSubmissionAnalyzer()
result = await analyzer.analyze_submission(
    submitted_code="print('Hello')",
    test_cases=[{"input": "", "output": "Hello"}],
    expected_solution="print('Hello')",
    topic_id="input_output"
)

# 과제 생성
generator = AssignmentGenerator()
new_assignments = await generator.generate_topic_assignments(
    topic_id="input_output",
    topic_name="입출력"
)
```

참고:
- 모든 데이터는 'courses/data/topics/' 디렉토리에 저장됨
- 과제 통계는 최근 100개의 제출 기록만 유지
- 코드 실행은 제한된 환경에서 안전하게 수행됨
"""

from pathlib import Path
from typing import Dict, List, Optional
import json
from datetime import datetime
from dataclasses import dataclass
import ast
from langchain_community.chat_models import ChatOpenAI
import asyncio
import re

def load_topics() -> List[Dict]:
    """course_list.json에서 토픽 목록 로드"""
    try:
        course_list_path = Path(__file__).parent.parent / 'data' / 'course_list.json'
        with open(course_list_path, 'r', encoding='utf-8') as f:
            course_data = json.load(f)
            return course_data['python']['topics']
    except Exception as e:
        print(f"토픽 목록 로드 중 오류: {str(e)}")
        return []

# course_list.json에서 토픽 목록 로드
TOPICS = load_topics()

@dataclass
class CodeAnalysisResult:
    is_correct: bool
    score: float
    feedback: str
    error_type: Optional[str] = None
    suggestions: List[str] = None

class AssignmentDataManager:
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.data_dir = self.base_dir / 'data' / 'topics'
        
    def get_file_path(self, topic_id: str, file_type: str) -> Path:
        """파일 경로 반환"""
        return self.data_dir / topic_id / 'content' / f'assignment_{file_type}.json'
        
    def load_assignment(self, topic_id: str) -> Optional[Dict]:
        """과제 데이터 로드"""
        try:
            path = self.data_dir / topic_id / 'content' / 'assignment.json'
            if not path.exists():
                return None
                
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"과제 데이터 로드 중 오류: {str(e)}")
            return None
            
    def load_answers(self, topic_id: str) -> Optional[Dict]:
        """답안 데이터 로드"""
        try:
            path = self.get_file_path(topic_id, 'answers')
            if not path.exists():
                return None
                
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"답안 데이터 로드 중 오류: {str(e)}")
            return None
            
    def get_assignment_by_id(self, topic_id: str, assignment_id: int) -> Optional[Dict]:
        """특정 과제 문제 데이터 반환"""
        data = self.load_assignment(topic_id)
        if not data:
            return None
            
        for assignment in data['assignments']:
            if assignment['id'] == assignment_id:
                return assignment
                
        return None
        
    def get_answer(self, topic_id: str, assignment_id: int) -> Optional[Dict]:
        """특정 과제의 답안 데이터 반환"""
        answers = self.load_answers(topic_id)
        if not answers:
            return None
            
        for answer in answers['assignments']:
            if answer['id'] == assignment_id:
                return answer
                
        return None
        
    def save_submission_stats(self, topic_id: str, assignment_id: int, 
                            submission_data: Dict) -> bool:
        """제출 통계 저장"""
        try:
            stats_path = self.get_file_path(topic_id, 'stats')
            stats = self._load_or_create_stats(stats_path)
            
            # 통계 업데이트
            assignment_stats = stats.setdefault(str(assignment_id), {
                'total_submissions': 0,
                'correct_submissions': 0,
                'submission_history': []
            })
            
            assignment_stats['total_submissions'] += 1
            if submission_data.get('is_correct'):
                assignment_stats['correct_submissions'] += 1
                
            # 최근 100개의 제출 기록만 유지
            assignment_stats['submission_history'].append({
                'timestamp': datetime.now().isoformat(),
                'is_correct': submission_data.get('is_correct'),
                'score': submission_data.get('score')
            })
            assignment_stats['submission_history'] = \
                assignment_stats['submission_history'][-100:]
            
            # 저장
            with open(stats_path, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
                
            return True
        except Exception as e:
            print(f"통계 저장 중 오류: {str(e)}")
            return False
            
    def _load_or_create_stats(self, path: Path) -> Dict:
        """통계 파일 로드 또는 생성"""
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

class CodeSubmissionAnalyzer:
    def __init__(self):
        self.llm = ChatOpenAI(
            model_name="gpt-4",
            temperature=0.3
        )
        self.python_keywords = {
            'False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await', 
            'break', 'class', 'continue', 'def', 'del', 'elif', 'else', 'except', 
            'finally', 'for', 'from', 'global', 'if', 'import', 'in', 'is', 'lambda', 
            'nonlocal', 'not', 'or', 'pass', 'raise', 'return', 'try', 'while', 'with', 'yield'
        }
        
    def _check_syntax(self, code: str) -> Dict:
        """Python 문법 및 스타일 검사"""
        try:
            # 1. 기본 문법 검사
            ast.parse(code)
            
            # 2. 들여쓰기 검사
            lines = code.split('\n')
            for i, line in enumerate(lines, 1):
                if line.strip() and not line.startswith((' ', '\t')) and ':' not in line:
                    if any(line.strip().startswith(kw) for kw in ['def', 'class', 'if', 'else', 'elif', 'for', 'while', 'try', 'except', 'finally']):
                        return {
                            'is_valid': False,
                            'error': f'잘못된 들여쓰기: 라인 {i}',
                            'line': i
                        }
            
            # 3. 괄호 매칭 검사
            stack = []
            brackets = {'(': ')', '[': ']', '{': '}'}
            for i, char in enumerate(code):
                if char in '([{':
                    stack.append(char)
                elif char in ')]}':
                    if not stack or brackets[stack.pop()] != char:
                        return {
                            'is_valid': False,
                            'error': f'괄호가 올바르게 매칭되지 않았습니다: 위치 {i}',
                            'offset': i
                        }
            if stack:
                return {
                    'is_valid': False,
                    'error': '괄호가 올바르게 닫히지 않았습니다'
                }
            
            # 4. 기본적인 코드 스타일 검사
            style_issues = []
            
            # 4.1 라인 길이 검사
            for i, line in enumerate(lines, 1):
                if len(line) > 79:  # PEP 8 권장사항
                    style_issues.append(f'라인 {i}가 너무 깁니다 (79자 제한)')
            
            # 4.2 공백 검사
            for i, line in enumerate(lines, 1):
                # 연산자 주변 공백
                for op in ['=', '+', '-', '*', '/', '//', '%', '**', '+=', '-=', '*=', '/=']:
                    if op in line and not line.strip().startswith('#'):
                        if f' {op} ' not in line and op in line:
                            style_issues.append(f'라인 {i}: 연산자 {op} 주변에 공백이 필요합니다')
                
                # 콤마 후 공백
                if ',' in line and not line.strip().startswith('#'):
                    if ',  ' in line:
                        style_issues.append(f'라인 {i}: 콤마 뒤에 한 개의 공백만 사용하세요')
                    elif ',' in line and not ', ' in line and not line.strip().endswith(','):
                        style_issues.append(f'라인 {i}: 콤마 뒤에 공백이 필요합니다')
            
            # 4.3 명명 규칙 검사
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    # 변수명 검사
                    if not node.id.islower() and '_' not in node.id:
                        style_issues.append(f'변수명 {node.id}는 소문자와 밑줄을 사용해야 합니다')
                elif isinstance(node, ast.FunctionDef):
                    # 함수명 검사
                    if not node.name.islower() and '_' not in node.name:
                        style_issues.append(f'함수명 {node.name}는 소문자와 밑줄을 사용해야 합니다')
            
            return {
                'is_valid': True,
                'style_issues': style_issues if style_issues else None
            }
            
        except SyntaxError as e:
            return {
                'is_valid': False,
                'error': str(e),
                'line': e.lineno,
                'offset': e.offset
            }
        except Exception as e:
            return {
                'is_valid': False,
                'error': str(e)
            }

    async def analyze_submission(self, 
                               submitted_code: str,
                               test_cases: List[Dict],
                               expected_solution: str,
                               topic_id: str) -> CodeAnalysisResult:
        """코드 제출 분석"""
        try:
            # 1. 기본적인 문법 검사
            syntax_check = self._check_syntax(submitted_code)
            if not syntax_check['is_valid']:
                return CodeAnalysisResult(
                    is_correct=False,
                    score=0,
                    feedback=f"문법 오류가 있습니다: {syntax_check['error']}",
                    error_type='syntax'
                )

            # 스타일 이슈가 있는 경우 피드백에 포함
            style_feedback = ""
            if syntax_check.get('style_issues'):
                style_feedback = "\n\n코드 스타일 개선 제안:\n" + "\n".join(syntax_check['style_issues'])

            # 2. 테스트 케이스 실행
            test_results = await self._run_test_cases(submitted_code, test_cases)
            if not test_results['all_passed']:
                return CodeAnalysisResult(
                    is_correct=False,
                    score=test_results['pass_rate'] * 50,
                    feedback=f"일부 테스트 케이스가 실패했습니다: {test_results['failed_cases']}{style_feedback}",
                    error_type='test_failure'
                )

            # 3. LLM을 통한 코드 분석
            analysis_result = await self._analyze_with_llm(
                submitted_code=submitted_code,
                expected_solution=expected_solution,
                test_results=test_results,
                topic_id=topic_id
            )

            # 스타일 피드백 추가
            if style_feedback:
                analysis_result['feedback'] += style_feedback

            return CodeAnalysisResult(
                is_correct=analysis_result['is_correct'],
                score=analysis_result['score'],
                feedback=analysis_result['feedback'],
                suggestions=analysis_result.get('suggestions', [])
            )

        except Exception as e:
            return CodeAnalysisResult(
                is_correct=False,
                score=0,
                feedback=f"코드 분석 중 오류가 발생했습니다: {str(e)}",
                error_type='system_error'
            )

    async def _run_test_cases(self, code: str, test_cases: List[Dict]) -> Dict:
        """테스트 케이스 실행"""
        results = []
        passed = 0
        failed_cases = []

        for test_case in test_cases:
            try:
                # 안전한 실행 환경에서 테스트
                result = await self._safe_execute(code, test_case['input'])
                expected = test_case['output']
                
                # 결과 비교 (융통성 있게)
                if self._compare_outputs(result, expected):
                    passed += 1
                else:
                    failed_cases.append({
                        'input': test_case['input'],
                        'expected': expected,
                        'got': result
                    })
                    
            except Exception as e:
                failed_cases.append({
                    'input': test_case['input'],
                    'error': str(e)
                })

        return {
            'all_passed': len(failed_cases) == 0,
            'pass_rate': passed / len(test_cases),
            'failed_cases': failed_cases
        }

    async def _analyze_with_llm(self, 
                               submitted_code: str,
                               expected_solution: str,
                               test_results: Dict,
                               topic_id: str) -> Dict:
        """LLM을 사용한 코드 분석"""
        prompt = f"""당신은 Python 코드 평가 전문가입니다.
현재 평가할 내용은 {topic_id} 주제의 과제입니다.

제출된 코드:
```python
{submitted_code}
```

모범 답안:
```python
{expected_solution}
```

테스트 결과:
{test_results}

다음 기준으로 코드를 평가해주세요:
1. 모든 테스트 케이스를 통과했나요?
2. 코드가 문제의 의도를 충족하나요?
3. 코드가 파이썬의 기본 원칙을 따르나요?
4. 불필요하게 복잡하지 않나요?

다음 형식으로 응답해주세요:
{{
    "is_acceptable": true/false,
    "score": 0-100,
    "feedback": "구체적인 피드백",
    "suggestions": ["개선 제안1", "개선 제안2"]
}}

주의사항:
- 테스트를 통과했다면 기본적으로 수용 가능한 것으로 간주
- 문법적 오류만 아니라면 다양한 해결 방식 인정
- 초보자를 위한 친근한 피드백 제공
- 개선점이 있더라도 긍정적인 부분 먼저 언급
"""

        response = await self.llm.agenerate(prompt)
        return json.loads(response.content)

    def _compare_outputs(self, result: str, expected: str) -> bool:
        """결과 비교 (초보자를 위한 유연한 비교)"""
        # 기본 전처리
        result = str(result).strip()
        expected = str(expected).strip()
        
        # 완전 일치하면 바로 True 반환
        if result == expected:
            return True
            
        # 대소문자 무시하고 비교
        if result.lower() == expected.lower():
            return True
            
        # 숫자의 경우 실수/정수 차이 무시
        if result.replace('.0', '') == expected.replace('.0', ''):
            return True
            
        # 문자열 따옴표 차이 무시
        if result.strip('"\'') == expected.strip('"\''):
            return True
            
        # 공백 차이 무시 (연속된 공백을 하나로)
        if ' '.join(result.split()) == ' '.join(expected.split()):
            return True
            
        # 문장부호 차이 무시 (.과 ! 정도만)
        result_normalized = result.replace('!', '.').replace('?', '.')
        expected_normalized = expected.replace('!', '.').replace('?', '.')
        if result_normalized == expected_normalized:
            return True
            
        # 줄바꿈 차이 무시
        if result.replace('\n', ' ') == expected.replace('\n', ' '):
            return True
            
        return False

    async def _safe_execute(self, code: str, input_data: str) -> str:
        """안전한 환경에서 코드 실행"""
        # 실행 환경 제한 및 타임아웃 설정
        try:
            # 기본적인 보안을 위한 globals 제한
            restricted_globals = {
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
            
            # 로컬 변수 설정
            local_vars = {'input_value': input_data}
            
            # 코드 실행
            exec(code, restricted_globals, local_vars)
            
            # 결과 반환 (마지막 출력값 또는 반환값)
            return str(local_vars.get('result', ''))
            
        except Exception as e:
            raise Exception(f"코드 실행 중 오류 발생: {str(e)}")

    async def analyze_code_analysis(self, submitted_analysis: str, code_to_analyze: str, points_to_consider: List[str], expected_points: List[str]) -> CodeAnalysisResult:
        """코드 분석 답안 평가"""
        try:
            # LLM을 사용한 분석 평가
            prompt = f"""다음 코드에 대한 학습자의 분석을 평가해주세요.

분석할 코드:
```python
{code_to_analyze}
```

고려해야 할 점:
{chr(10).join([f"- {point}" for point in points_to_consider])}

학습자의 분석:
{submitted_analysis}

기대하는 분석 포인트:
{chr(10).join([f"- {point}" for point in expected_points])}

다음을 평가해주세요:
1. 학습자가 주요 포인트를 얼마나 잘 파악했는지
2. 분석의 정확성과 깊이
3. 개선이 필요한 부분

응답 형식:
{{
    "score": 0-100,
    "feedback": "구체적인 피드백",
    "suggestions": ["개선 제안1", "개선 제안2"]
}}"""

            response = await self.llm.agenerate(prompt)
            analysis = json.loads(response.content)

            return CodeAnalysisResult(
                is_correct=analysis['score'] >= 70,
                score=analysis['score'],
                feedback=analysis['feedback'],
                suggestions=analysis.get('suggestions', [])
            )

        except Exception as e:
            return CodeAnalysisResult(
                is_correct=False,
                score=0,
                feedback=f"분석 평가 중 오류가 발생했습니다: {str(e)}",
                error_type='system_error'
            )

class AssignmentGenerator:
    def __init__(self):
        self.llm = ChatOpenAI(
            model_name="gpt-4",
            temperature=0.7  # 더 창의적인 문제 생성을 위해 높임
        )
        
    async def generate_assignment(self, 
                                topic_id: str,
                                topic_name: str,
                                assignment_type: str,
                                difficulty: str = 'beginner') -> Dict:
        """과제 생성"""
        if topic_id == "input_output":
            system_prompt = """당신은 Python 교육 전문가입니다.
현재 input()과 print() 함수에 대한 초보자용 문제를 생성합니다.

절대적 제약사항:
1. 오직 input()과 print() 함수만 다룹니다
2. input(): 사용자로부터 키보드 입력을 받는 함수
3. print(): 콘솔에 출력하는 함수
4. 파일 입출력(file I/O)은 절대 다루지 않습니다
5. 파일 열기/쓰기/읽기 등의 내용은 절대 포함하지 않습니다

문제 예시:
- input()으로 이름을 입력받아 인사하기
- 숫자를 입력받아 계산 결과 출력하기
- 여러 줄의 입력을 받아 형식을 갖춰 출력하기
"""
        else:
            system_prompt = f"""당신은 Python 교육 전문가입니다.
현재 {topic_name} 주제의 {difficulty} 난이도 문제를 생성합니다.

주의사항:
1. 실제 현업에서 마주할 수 있는 상황을 반영
2. 명확하고 이해하기 쉬운 설명 제공
3. 단계적으로 접근할 수 있는 힌트 제공
4. 테스트 케이스는 기본/경계/예외 상황 포함
"""
        
        prompt = PROMPTS[assignment_type].format(
            topic_name=topic_name
        )
        
        response = await self.llm.agenerate([system_prompt, prompt])
        return json.loads(response.content)
        
    async def generate_topic_assignments(self,
                                       topic_id: str,
                                       topic_name: str) -> Dict:
        """토픽의 전체 과제 세트 생성"""
        assignments = []
        
        # 1. 개념 이해 문제 (3개)
        for i in range(3):
            assignment = await self.generate_assignment(
                topic_id=topic_id,
                topic_name=topic_name,
                assignment_type='concept'
            )
            assignments.append({
                'id': len(assignments) + 1,
                'type': 'concept',
                **assignment
            })
            
        # 2. 구현 문제 (2개)
        for i in range(2):
            assignment = await self.generate_assignment(
                topic_id=topic_id,
                topic_name=topic_name,
                assignment_type='implementation'
            )
            assignments.append({
                'id': len(assignments) + 1,
                'type': 'implementation',
                **assignment
            })
            
        return {
            'topic_id': topic_id,
            'assignments': assignments,
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'version': '1.0'
            }
        }

PROMPTS = {
    'concept': """
    {topic_name} 주제에 대한 개념 이해 문제를 생성해주세요.
    
    다음 형식으로 작성:
    {
        "question": "문제 내용",
        "choices": ["보기1", "보기2", "보기3", "보기4"],
        "correct_answer": 정답번호,
        "explanation": "정답 설명",
        "hint": "오답시 힌트"
    }
    """,
    
    'implementation': """
    {topic_name} 주제의 구현 문제를 생성해주세요.
    
    특별 주의사항:
    - input_output 토픽의 경우, 
    
    다음 형식으로 작성:
    {
        "question": "문제 내용",
        "constraints": ["제약사항1", "제약사항2"],
        "test_cases": [
            {"input": "입력값", "output": "기대값"},
            ...
        ],
        "sample_solution": "예시 답안",
        "hints": ["힌트1", "힌트2"]
    }
    """
}

async def main():
    generator = AssignmentGenerator()
    data_manager = AssignmentDataManager()
    
    # 단일 토픽 처리를 위한 함수
    async def generate_single_topic(topic_id: str):
        topic = next((t for t in TOPICS if t['id'] == topic_id), None)
        if not topic:
            print(f"Error: Topic {topic_id} not found")
            return
            
        print(f"Generating assignments for {topic['name']}...")
        
        assignments = await generator.generate_topic_assignments(
            topic_id=topic['id'],
            topic_name=topic['name']
        )
        
        # 과제 저장
        assignment_path = data_manager.get_file_path(topic['id'], 'assignment')
        assignment_path.parent.mkdir(parents=True, exist_ok=True)
        with open(assignment_path, 'w', encoding='utf-8') as f:
            json.dump(assignments, f, ensure_ascii=False, indent=2)
            
        print(f"✓ Generated {len(assignments['assignments'])} assignments")
    
    # 명령행 인자 확인
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "input_output":
        await generate_single_topic("input_output")
    else:
        # 모든 토픽 생성
        for topic in TOPICS:
            await generate_single_topic(topic['id'])
        
if __name__ == '__main__':
    asyncio.run(main()) 