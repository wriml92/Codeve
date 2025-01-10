<<<<<<< HEAD
# PythonTutor

update
=======
### 프로젝트 구조
```
Codeve/
│
├── accounts/             # 사용자 및 인증 관리
│   ├── templates/accounts/ # 회원가입, 로그인 페이지
│   ├── models.py         # User, Authentication 관련 모델
│   ├── views.py          # 로그인, 회원가입 등 인증 관련 엔드포인트
│   ├── serializers.py    # API 데이터 직렬화
│   └── urls.py           # accounts 관련 엔드포인트 라우팅
│
├── courses/              # 강좌 및 학습 관리
│   ├── templates/courses/ # 강좌 페이지
│   ├── models.py         # Course, Lesson, Quiz 관련 모델
│   ├── views.py          # 강좌 CRUD 및 퀴즈 관련 엔드포인트
│   ├── serializers.py    # 강좌/학습 데이터 직렬화
│   └── urls.py           # courses 관련 엔드포인트 라우팅
│
├── roadmaps/             # 학습 경로 관리
│   ├── templates/roadmaps/ # 학습 경로 페이지
│   ├── models.py         # Roadmap 및 Step 관련 모델
│   ├── views.py          # 학습 경로 CRUD 및 유저 진행 상황 처리
│   ├── serializers.py    # 학습 경로 데이터 직렬화
│   └── urls.py           # roadmaps 관련 엔드포인트 라우팅
│
├── communities/          # 커뮤니티 기능
│   ├── templates/communities/ # 커뮤니티 페이지
│   ├── models.py         # Post, Comment 모델
│   ├── views.py          # 게시글, CRUD 처리
│   ├── serializers.py    # 데이터 직렬화
│   └── urls.py           # community 관련 엔드포인트 라우팅
│
├── ai_services/          # AI 관련 기능
│   ├── templates/ai_services/ # AI 서비스 페이지
│   ├── gpt_chatbot.py    # GPT 기반 Python 학습 챗봇
│   ├── rag_chatbot.py    # RAG 기반 챗봇
│   └── utils.py          # AI 서비스 관련 유틸리티 함수
│
├── performances/         # 성과 관리
│   ├── templates/performances/ # 성과 관리 페이지
│   ├── models.py         # UserPerformance, Performance 관련 모델
│   ├── views.py          # 성과 관리 API 엔드포인트
│   ├── serializers.py    # 데이터 직렬화
│   └── urls.py           # performance 관련 엔드포인트 라우팅
│
├── Codeve/              # 프로젝트 설정
│   ├── __init__.py      # Python 패키지 선언
│   ├── asgi.py          # ASGI 설정
│   ├── settings.py      # Django 설정 파일
│   ├── urls.py          # 전역 URL 라우팅
│   └── wsgi.py          # WSGI 설정
│
├── manage.py            # Django 관리 스크립트
└── requirements.txt     # 프로젝트 의존성 목록
```

### ERD 다이어그램
```
%% 사용자 관리
    User {
        int id PK
        string email "Unique"
        string password "Nullable"
        string google_id "Nullable"
        string username
        datetime created_at
        datetime updated_at
    }

    SocialAccount {
        int id PK
        int user_id FK
        string provider "예: Google"
        string social_id "OAuth에서 제공받는 유저 ID"
        datetime created_at
        datetime updated_at
    }

    UserCourse {
        int id PK
        int user_id FK
        int course_id FK
        string status "enrolled/completed/in_progress"
        int progress_percentage
        datetime enrolled_at
        datetime completed_at
        datetime last_accessed_at
        datetime created_at
        datetime updated_at
    }

    %% 학습 콘텐츠 관리
    Course {
        int id PK
        string title "예: Python 기초"
        text description
        int difficulty_level
        datetime created_at
        datetime updated_at
    }

    Lesson {
        int id PK
        int course_id FK
        string title
        text content
        int order
        datetime created_at
        datetime updated_at
    }

    Quiz {
        int id PK
        int lesson_id FK
        string question
        text answer_options "JSON 형식으로 저장"
        string correct_answer
        datetime created_at
        datetime updated_at
    }

    PracticeExercise {
        int id PK
        int lesson_id FK
        string title
        text description
        text initial_code
        text solution_code
        text test_cases "JSON 형식으로 저장"
        datetime created_at
        datetime updated_at
    }

    %% 게시판
    Post {
        int id PK
        int user_id FK
        string title
        text content
        datetime created_at
        datetime updated_at
    }

    %% AI 상호작용
    AI_Interaction {
        int id PK
        int user_id FK
        text prompt
        text response
        datetime created_at
        datetime updated_at
    }

    %% 로드맵
    LearningRoadmap {
        int id PK
        string title
        text description
        datetime created_at
        datetime updated_at
    }

    RoadmapStep {
        int id PK
        int roadmap_id FK
        string title
        text content
        int step_order
        datetime created_at
        datetime updated_at
    }

    UserRoadmapProgress {
        int id PK
        int user_id FK
        int roadmap_step_id FK
        string status "not_started, in_progress, completed"
        datetime started_at "Nullable"
        datetime completed_at "Nullable"
        datetime created_at
        datetime updated_at
    }

    %% 성과 관리 시스템
    Performance {
        int id PK
        string name "예: 퀴즈 성공률, 실습 완료율"
        text description
        int target_percentage "목표 달성 기준 퍼센트"
        datetime created_at
        datetime updated_at
    }

    UserPerformance {
        int id PK
        int user_id FK
        int performance_id FK
        float achievement_rate "달성률(%)"
        datetime achieved_at "Nullable"
        datetime created_at
        datetime updated_at
    }

    %% Relationships
    User ||--o{ SocialAccount : "has"
    User ||--o{ Post : "writes"
    User ||--o{ AI_Interaction : "interacts"
    User ||--o{ UserRoadmapProgress : "progresses"
    User ||--o{ UserCourse : "enrolls"
    User ||--o{ UserPerformance : "achieves"

    Course ||--o{ Lesson : "contains"
    Course ||--o{ UserCourse : "has_students"
    
    Lesson ||--o{ Quiz : "has"
    Lesson ||--o{ PracticeExercise : "includes"
    
    LearningRoadmap ||--o{ RoadmapStep : "includes"
    RoadmapStep ||--o{ UserRoadmapProgress : "tracked by"
    Performance ||--o{ UserPerformance : "tracked by"
```

### 기술 스택
| **분류** | **사용 기술** |
| --- | --- |
| **프로그래밍 언어** | Python, JavaScript |
| **백엔드 프레임워크** | Django REST Framework (DRF) |
| **프론트엔드** | Django 템플릿, Tailwind CSS 또는 Bootstrap |
| **데이터베이스** | PostgreSQL |
| **AI 및 분석 도구** | OpenAI GPT API, LangChain, FAISS |
| **협업 도구** | Google Docs, GitHub, Notion, Slack |
>>>>>>> 86e4db7 (Initial commit from origin/hyuk to develop)
