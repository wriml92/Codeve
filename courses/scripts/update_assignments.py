import json
import os
from pathlib import Path
from typing import Dict, Any

def add_submit_button(section_content: str, quiz_number: int, quiz_type: str) -> str:
    """섹션에 제출 버튼과 결과 표시 영역 추가"""
    button_html = f"""
            <button onclick="submitQuiz({quiz_number}, '{quiz_type}')" class="mt-6 w-full px-6 py-3 bg-gradient-to-r from-amber-500 to-yellow-400 text-white font-semibold rounded-xl shadow-md hover:shadow-lg transform hover:-translate-y-0.5 transition-all duration-200 hover:from-amber-600 hover:to-yellow-500 flex items-center justify-center">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                {quiz_type.replace('concept', '개념 이해').replace('analysis', '코드 분석').replace('implementation', '코드 구현')} 제출하기
            </button>
            <div id="result{quiz_number}" class="mt-4 hidden">
                <div class="p-4 rounded-lg"></div>
            </div>"""
    
    # 섹션 끝 부분에 버튼 추가
    if "</div>\n    </section>" in section_content:
        return section_content.replace("</div>\n    </section>", f"{button_html}\n        </div>\n    </section>")
    return section_content

def add_code_editor(section_content: str, editor_number: int) -> str:
    """코드 에디터 추가"""
    editor_html = f"""
            <div class="code-editor-container">
                <div id="editor{editor_number}" class="code-editor"></div>
            </div>"""
    
    # 코드 분석 문제의 경우 예시 코드 다음에 에디터 추가
    if "bg-gray-900 rounded-lg p-4 my-4" in section_content:
        return section_content.replace("</pre>\n            </div>", f"</pre>\n            </div>{editor_html}")
    # 코드 구현 문제의 경우 기존 코드 영역을 에디터로 교체
    else:
        return section_content.replace(
            """<div class="bg-gray-900 rounded-lg p-4 my-4">
                <pre class="text-white font-mono text-sm overflow-x-auto">
{초기 코드}
                </pre>
            </div>""", 
            editor_html
        )

def update_assignment_content(content: str) -> str:
    """과제 내용 업데이트"""
    sections = content.split("<section")
    updated_sections = []
    
    for i, section in enumerate(sections):
        if i == 0:  # 첫 부분은 섹션이 아님
            updated_sections.append(section)
            continue
            
        section = "<section" + section
        
        # 개념 이해 문제
        if "개념 이해" in section:
            section = add_submit_button(section, 1, 'concept')
        
        # 코드 분석 문제
        elif "코드 분석" in section:
            section = add_code_editor(section, 2)
            section = add_submit_button(section, 2, 'analysis')
            
        # 코드 구현 문제
        elif "코드 구현" in section:
            section = add_code_editor(section, 3)
            section = add_submit_button(section, 3, 'implementation')
            
        updated_sections.append(section)
    
    return "".join(updated_sections)

def update_assignments():
    """모든 토픽의 과제 파일 업데이트"""
    base_dir = Path(__file__).parent.parent
    
    # course_list.json에서 토픽 목록 가져오기
    with open(base_dir / 'data' / 'course_list.json', 'r', encoding='utf-8') as f:
        course_list = json.load(f)
    
    # 각 토픽의 과제 파일 업데이트
    for topic in course_list['python']['topics']:
        topic_id = topic['id']
        assignment_path = base_dir / 'data' / 'topics' / topic_id / 'content' / 'assignment.json'
        
        if assignment_path.exists():
            print(f"Updating {topic_id}/assignment.json...")
            
            # 파일 읽기
            with open(assignment_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 내용 업데이트
            content = data['content']
            if not "submitQuiz" in content:  # 아직 업데이트되지 않은 경우만
                data['content'] = update_assignment_content(content)
                
                # 파일 저장
                with open(assignment_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"✅ Updated {topic_id}/assignment.json")
            else:
                print(f"⏭️ Skipped {topic_id}/assignment.json (already updated)")

if __name__ == "__main__":
    update_assignments() 