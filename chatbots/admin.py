from django.contrib import admin
from .models import ChatMessage


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('user', 'short_message', 'created_at')
    list_filter = ('created_at', 'user')
    search_fields = ('message', 'response', 'user__username')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'

    def short_message(self, obj):
        """메시지 내용을 짧게 표시"""
        return (obj.message[:50] + '...') if len(obj.message) > 50 else obj.message
    short_message.short_description = '메시지'
