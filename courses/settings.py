STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
    ('topics', BASE_DIR / 'courses' / 'data' / 'topics'),  # 이론 내용 디렉토리
]

STATIC_ROOT = BASE_DIR / 'staticfiles'

# 정적 파일 캐싱 설정
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage' 