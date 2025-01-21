from django.apps import AppConfig
from django.conf import settings


class ChatbotsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chatbots'

    def ready(self):
        if not settings.OPENAI_API_KEY:
            raise Exception("OPENAI_API_KEY is not set")
