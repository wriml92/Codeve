from typing import Dict, Any, List
from pathlib import Path
import json
from datetime import datetime
import yaml  # config 파일 로드를 위해 추가
import asyncio

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
            current_dir = topic_dir / 'current'
            current_dir.mkdir(parents=True, exist_ok=True)

            if content_type in ['all', 'theory']:
                await self.generate_theory(topic_id)
            
            if content_type in ['all', 'practice']:
                # practice 내용 생성
                practice_content = await self.practice_llm.generate(topic_id)
                
                # practice.json 파일 저장
                practice_file = current_dir / 'practice.json'
                with open(practice_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'content': practice_content,
                        'metadata': {
                            'created_at': datetime.now().isoformat(),
                            'version': 1
                        }
                    }, f, indent=2, ensure_ascii=False)
                print(f"✅ {topic_id} practice 내용 생성 완료")
            
            if content_type in ['all', 'assignment']:
                self.initialize_templates(topic_id)
                await self.assignment_llm.generate(topic_id)

        except Exception as e:
            print(f"❌ {topic_id} 생성 중 오류 발생: {str(e)}")
            raise

    async def generate_theory(self, topic_id: str):
        """이론 내용 생성"""
        try:
            # 1. 디렉토리 구조 생성
            topic_dir = self.data_dir / topic_id
            versions_dir = topic_dir / 'versions'
            versions_dir.mkdir(parents=True, exist_ok=True)
            
            # 2. 새 버전 디렉토리 생성
            new_version = self._get_next_version(versions_dir)
            version_dir = versions_dir / f'v{new_version}'
            version_dir.mkdir(parents=True, exist_ok=True)

            # 3. 새 내용 생성
            theory_content = await self.theory_llm.generate(topic_id)
            
            # 4. 품질 평가
            quality_score = self._evaluate_content(theory_content, topic_id)
            
            # 5. 저장
            theory_file = version_dir / 'theory.json'
            with open(theory_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'content': theory_content,
                    'metadata': {
                        'version': new_version,
                        'created_at': datetime.now().isoformat(),
                        'quality_score': quality_score
                    }
                }, f, indent=2, ensure_ascii=False)
            
            # 6. current 디렉토리 생성 및 심볼릭 링크 설정
            current_dir = topic_dir / 'current'
            current_dir.mkdir(exist_ok=True)
            
            current_file = current_dir / 'theory.json'
            if current_file.exists():
                current_file.unlink()
            current_file.symlink_to(theory_file)
            
            return f"새로운 버전(v{new_version})이 생성되었습니다. (품질 점수: {quality_score})"
            
        except Exception as e:
            print(f"이론 생성 중 오류 발생: {str(e)}")
            import traceback
            print(traceback.format_exc())
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

    def _get_next_version(self, versions_dir: Path) -> int:
        """다음 버전 번호 가져오기"""
        versions = [int(f.name.split('v')[1]) for f in versions_dir.glob('v*') if f.is_dir()]
        return max(versions, default=0) + 1

    def _get_current_score(self, topic_id: str) -> float:
        """현재 버전의 품질 점수 가져오기"""
        topic_dir = self.data_dir / topic_id
        versions_dir = topic_dir / 'versions'
        if versions_dir.is_dir():
            versions = [f for f in versions_dir.glob('v*') if f.is_dir()]
            if versions:
                latest_version_dir = max(versions, key=lambda f: int(f.name.split('v')[1]))
                with open(latest_version_dir / 'theory.json', 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    return metadata['metadata']['quality_score']
        return 0.0

    def _update_current_version(self, topic_id: str, new_version: int):
        """current 심볼릭 링크 업데이트"""
        topic_dir = self.data_dir / topic_id
        current_link = topic_dir / 'current'
        current_link.unlink(missing_ok=True)
        current_link.symlink_to(f'v{new_version}')

    def initialize_templates(self, topic_id: str):
        """템플릿 확인/생성"""
        # 템플릿 확인/생성 로직을 구현해야 합니다.
        pass

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