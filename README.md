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
│   ├── models.py         # Course, Lesson, Assignment 관련 모델
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

### 기술 스택
| **분류** | **사용 기술** |
| --- | --- |
| **프로그래밍 언어** | Python, JavaScript |
| **백엔드 프레임워크** | Django REST Framework (DRF) |
| **프론트엔드** | Django 템플릿, Tailwind CSS 또는 Bootstrap |
| **데이터베이스** | PostgreSQL |
| **AI 및 분석 도구** | OpenAI GPT API, LangChain, FAISS |
| **협업 도구** | Google Docs, GitHub, Notion, Slack |