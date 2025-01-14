# Courses API 문서

## 1. 이론 내용 생성 API
기능명: 이론 내용 생성
유형: POST
URL: /api/v1/courses/{course_id}/theory
설명: 새로운 이론 내용을 생성
요청 파라미터:
- title: string (필수) - 이론 제목
- content: string (필수) - 이론 내용
응답:
- 성공: 201 Created
- 실패: 400 Bad Request


## 2. 이론 내용 조회 API
기능명: 이론 내용 조회
유형: GET
URL: /api/v1/courses/{course_id}/theory
설명: 특정 코스의 이론 내용을 조회
응답:
- 성공: 200 OK
- 실패: 404 Not Found

## 3. 이론 데이터 기반 실습 생성 API
- **기능명**: 이론 데이터 기반 실습 생성  
- **유형**: POST  
- **URL**: `/api/v1/courses/{course_id}/practice`  
- **설명**: 이론 내용을 기반으로 실습 데이터를 생성  
- **요청 파라미터**:  
  - `instructions`: string (필수) - 실습 지침  
- **제한 사항**:  
  - 각 코스당 사용자별 최대 **10회 이미지 처리**로 제한됩니다.
  - 제한 초과 시, `429 Too Many Requests` 응답과 함께 남은 대기 시간을 반환합니다.  
- **응답**:  
  - 성공: `201 Created`  
  - 실패:  
    - `429 Too Many Requests`
    - `400 Bad Request`

## 4. 실습 데이터 조회 API
기능명: 실습 데이터 조회
유형: GET
URL: /api/v1/courses/{course_id}/practice
설명: 실습 데이터를 조회
응답:
- 성공: 200 OK
- 실패: 404 Not Found

## 5. 퀴즈 관리 API

### 5.1. 미리 생성된 퀴즈 관리 API
기능명: 미리 생성된 퀴즈 관리
유형: GET
URL: /api/v1/courses/{course_id}/quizzes
설명: 미리 생성된 퀴즈 목록을 가져옴
응답:
- 성공: 200 OK
- 실패: 404 Not Found

### 5.2. 실시간 생성 퀴즈 요청 API
기능명: 실시간 생성 퀴즈 요청
유형: GET
URL: /api/v1/courses/{course_id}/quizzes/live
설명: 실시간으로 생성된 퀴즈 요청
응답:
- 성공: 200 OK
- 실패: 400 Bad Request

## 5.3. 사용자 퀴즈 제출 및 채점 API
- **기능명**: 사용자 퀴즈 제출 및 채점  
- **유형**: POST  
- **URL**: `/api/v1/courses/{course_id}/quizzes/submit`  
- **설명**: 
  - 사용자 퀴즈 제출 및 정답 확인.
  - **코드쉘 연동**을 통해 사용자가 코드 실행 결과를 확인할 수 있음.
- **요청 파라미터**:  
  - `quiz_id`: int (필수) - 퀴즈 ID  
  - `answer`: string (필수) - 사용자 답변  
  - `code_input`: string (선택) - 코드쉘에 실행할 사용자 코드  
- **응답**:  
  - 성공: `200 OK`  
  - 실패: `400 Bad Request`  
  - 코드 실행 결과 포함:
    ```json
    {
      "is_correct": true,
      "feedback": "Your code executed successfully!",
      "execution_result": "Output: 42"
    }
    ```

## 6. 분석 데이터 수집 API
기능명: 분석 데이터 수집
유형: POST
URL: /api/v1/courses/{course_id}/analysis
설명: 과제와 퀴즈 데이터를 수집
요청 파라미터:
user_id: int (필수) - 사용자 ID
image_success: boolean (선택) - 이미지 과제 성공 여부
quiz_success: boolean (선택) - 퀴즈 성공 여부
응답:
- 성공: 200 OK
- 실패: 400 Bad Request

## 7. 학습 경로 제안 API
기능명: 학습 경로 제안
유형: GET
URL: /api/v1/courses/{course_id}/recommendations
설명: 사용자의 학습 결과를 분석하여 학습 경로를 추천
응답:
- 성공: 200 OK
- 실패: 400 Bad Request

## 8. 회고 데이터 및 결과 API

### 8.1. 회고 데이터 수집 API
기능명: 회고 데이터 수집
유형: POST
URL: /api/v1/courses/{course_id}/reflection/data
설명: 각 에이전트에서 생성된 데이터를 수집
응답:
- 성공: 200 OK
- 실패: 400 Bad Request

### 8.2. 회고 문장 생성 API
기능명: 회고 문장 생성
유형: POST
URL: /api/v1/courses/{course_id}/reflection
설명: 수집된 데이터를 기반으로 회고 문장을 생성
응답:
- 성공: 200 OK
- 실패: 400 Bad Request

