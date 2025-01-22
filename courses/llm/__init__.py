from typing import Dict, Any, List
from pathlib import Path
import json
from datetime import datetime
import yaml  # config 파일 로드를 위해 추가
import asyncio
import shutil

# LLM 클래스들 import
from .theory_llm import TheoryLLM
from .practice_llm import PracticeLLM
from .assignment_llm import AssignmentLLM

class ContentGenerator:
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        # course_list.json 경로 수정
        self.course_list_path = self.base_dir / 'data' / 'course_list.json'
        self.data_dir = self.base_dir / 'data' / 'topics'
        self.config = self.load_config()
        self.theory_llm = TheoryLLM()
        self.practice_llm = PracticeLLM()
        self.assignment_llm = AssignmentLLM()

    def load_config(self) -> Dict:
        """설정 파일 로드"""
        config_path = self.base_dir / 'config' / 'generation.yaml'
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"Warning: {config_path} 파일을 찾을 수 없습니다. 기본 설정을 사용합니다.")
            return {
                'generation': {
                    'batch_size': 5,
                    'delay': 2,
                    'retries': 3
                },
                'validation': {
                    'required_sections': {
                        'theory': [
                            "개념 소개",
                            "비유",
                            "핵심 포인트"
                        ],
                        'practice': [
                            "실습 환경",
                            "예제",
                            "실행 방법"
                        ],
                        'assignment': [
                            "문제",
                            "채점 기준",
                            "피드백"
                        ]
                    }
                }
            }

    async def generate_topic(self, topic_id: str, content_type: str = 'all', force: bool = False):
        """단일 토픽 콘텐츠 생성"""
        try:
            topic_dir = self.data_dir / topic_id
            content_dir = topic_dir / 'content'
            versions_dir = topic_dir / 'versions'
            
            # 디렉토리 구조 생성
            content_dir.mkdir(parents=True, exist_ok=True)
            versions_dir.mkdir(exist_ok=True)
            
            if content_type in ['all', 'theory']:
                # 이론 내용 생성
                theory_content = await self.theory_llm.generate(topic_id)
                
                # content 디렉토리에 저장
                theory_file = content_dir / 'theory.json'
                with open(theory_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'content': theory_content,  # HTML 콘텐츠
                        'metadata': {
                            'created_at': datetime.now().isoformat(),
                            'version': 1
                        }
                    }, f, indent=2, ensure_ascii=False)
                
                # versions에 백업
                v1_dir = versions_dir / 'v1'
                v1_dir.mkdir(exist_ok=True)
                shutil.copy2(theory_file, v1_dir / 'theory.json')
                
                print(f"✅ {topic_id} theory 내용 생성 완료")
            
            if content_type in ['all', 'practice']:
                # practice 내용 생성
                practice_content = await self.practice_llm.generate(topic_id)
                
                # content 디렉토리에 저장
                practice_file = content_dir / 'practice.json'
                with open(practice_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'content': practice_content,
                        'metadata': {
                            'created_at': datetime.now().isoformat(),
                            'version': 1
                        }
                    }, f, indent=2, ensure_ascii=False)
                
                # versions에 백업
                v1_dir = versions_dir / 'v1'
                v1_dir.mkdir(exist_ok=True)
                shutil.copy2(practice_file, v1_dir / 'practice.json')
                
                print(f"✅ {topic_id} practice 내용 생성 완료")
            
            if content_type in ['all', 'assignment']:
                # assignment 내용 생성
                assignment_content = await self.assignment_llm.generate(topic_id)
                
                # content 디렉토리에 저장
                assignment_file = content_dir / 'assignment.json'
                with open(assignment_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'content': assignment_content,
                        'metadata': {
                            'created_at': datetime.now().isoformat(),
                            'version': 1
                        }
                    }, f, indent=2, ensure_ascii=False)
                
                # versions에 백업
                v1_dir = versions_dir / 'v1'
                v1_dir.mkdir(exist_ok=True)
                shutil.copy2(assignment_file, v1_dir / 'assignment.json')
                
                print(f"✅ {topic_id} assignment 내용 생성 완료")
            
            # version.json 생성/업데이트
            version_info = {
                "current_version": "v1",
                "updated_at": datetime.now().isoformat(),
                "content": {
                    "theory": {
                        "version": "v1",
                        "path": "content/theory.json"
                    },
                    "practice": {
                        "version": "v1",
                        "path": "content/practice.json"
                    },
                    "assignment": {
                        "version": "v1",
                        "path": "content/assignment.json"
                    }
                }
            }
            
            with open(topic_dir / 'version.json', 'w', encoding='utf-8') as f:
                json.dump(version_info, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print(f"❌ {topic_id} 생성 중 오류 발생: {str(e)}")
            raise

    def _evaluate_content(self, content: str, topic_id: str) -> float:
        """콘텐츠 품질 평가"""
        score = 0.0
        max_score = 100.0
        
        try:
            # 1. 필수 섹션 확인 (40점)
            required_sections = ["개념 소개", "비유", "핵심 포인트"]  # 기본값 직접 지정
            if isinstance(self.config, dict):  # config가 딕셔너리인 경우에만 시도
                validation = self.config.get('validation', {})
                if isinstance(validation, dict):
                    sections = validation.get('required_sections', {})
                    if isinstance(sections, dict):
                        theory_sections = sections.get('theory', [])
                        if theory_sections:
                            required_sections = theory_sections
            
            sections_score = 0
            for section in required_sections:
                if section in content:
                    sections_score += 40 / len(required_sections)
            
            # 2. 가독성 체크 (20점)
            readability_score = 20.0
            if len(content.split('\n\n')) < 3:  # 단락 구분
                readability_score *= 0.5
            
            # 3. 예제 포함 여부 (20점)
            example_score = 20.0
            if '```' in content:
                example_score = 0.0
            
            # 총합 계산
            quality_score = sections_score + readability_score + example_score
            
            return quality_score
        
        except Exception as e:
            print(f"품질 평가 중 오류 발생: {str(e)}")
            import traceback
            print(traceback.format_exc())  # 상세한 오류 정보 출력
            return 0.0

    async def generate_all(self, content_type: str = 'all', force: bool = False):
        """모든 토픽의 콘텐츠 생성"""
        try:
            # course_list.json 로드
            with open(self.course_list_path, 'r', encoding='utf-8') as f:
                course_list = json.load(f)

            # Python 코스의 토픽 목록 가져오기
            python_course = course_list['python']
            if not python_course.get('topics'):
                print("토픽 목록이 비어있습니다.")
                return []

            results = []
            for topic in python_course['topics']:
                topic_id = topic['id']
                print(f"\n=== {topic_id} 콘텐츠 생성 시작 ===")
                try:
                    await self.generate_topic(topic_id, content_type, force)
                    results.append({
                        'topic_id': topic_id,
                        'status': 'success'
                    })
                    print(f"✅ {topic_id} 생성 완료")
                except Exception as e:
                    results.append({
                        'topic_id': topic_id,
                        'status': 'error',
                        'error': str(e)
                    })
                    print(f"❌ {topic_id} 생성 실패: {str(e)}")
                
                # API 호출 제한 고려
                await asyncio.sleep(self.config['generation']['delay'])
            
            # 최종 결과 출력
            print("\n=== 생성 결과 요약 ===")
            success = len([r for r in results if r['status'] == 'success'])
            failed = len([r for r in results if r['status'] == 'error'])
            print(f"성공: {success}, 실패: {failed}")
            
            return results
        
        except FileNotFoundError:
            print(f"❌ course_list.json 파일을 찾을 수 없습니다: {self.course_list_path}")
            raise
        except Exception as e:
            print(f"콘텐츠 생성 중 오류 발생: {str(e)}")
            raise

    @staticmethod
    def get_content_types() -> List[str]:
        """사용 가능한 콘텐츠 타입 목록 반환"""
        return ['theory', 'practice', 'assignment']

    def get_content_path(self, topic_id: str, content_type: str) -> Path:
        """콘텐츠 파일 경로 반환"""
        topic_dir = self.data_dir / topic_id
        
        # version.json 읽기
        with open(topic_dir / 'version.json', 'r', encoding='utf-8') as f:
            version_info = json.load(f)
        
        # 현재 버전의 파일 경로 반환
        content_path = version_info['content'][content_type]['path']
        return topic_dir / content_path