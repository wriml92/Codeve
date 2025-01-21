from django.contrib import admin
from .models import ChatMessage, CachedResponse


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'created_at', 'is_cached')
    list_filter = ('is_cached', 'created_at')
    search_fields = ('message', 'response')


@admin.register(CachedResponse)
class CachedResponseAdmin(admin.ModelAdmin):
    list_display = ('question', 'created_at', 'updated_at')
    search_fields = ('question', 'response')
