"""
Admin configuration for RAG app
"""
from django.contrib import admin
from .models import Project, FileIndex, TextChunk, ChatSession, ChatMessage, RAGConfig, FileWatchEvent


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'total_files', 'created_at', 'last_indexed', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'folder_path']
    readonly_fields = ['created_at', 'updated_at', 'last_indexed']

    fieldsets = (
        ('Project Information', {
            'fields': ('name', 'description', 'folder_path')
        }),
        ('Status', {
            'fields': ('is_active', 'total_files', 'last_indexed')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
    )


@admin.register(FileIndex)
class FileIndexAdmin(admin.ModelAdmin):
    list_display = ['file_name', 'project', 'file_type', 'chunk_count', 'indexed_at']
    list_filter = ['file_type', 'project', 'indexed_at']
    search_fields = ['file_name', 'file_path']
    readonly_fields = ['indexed_at', 'content_hash']


@admin.register(TextChunk)
class TextChunkAdmin(admin.ModelAdmin):
    list_display = ['file_index', 'chunk_index', 'start_line', 'end_line']
    list_filter = ['file_index', 'created_at']
    search_fields = ['file_index__file_name', 'content']
    readonly_fields = ['created_at']


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ['title', 'project', 'message_count', 'created_at', 'is_archived']
    list_filter = ['project', 'created_at', 'is_archived']
    search_fields = ['title', 'project__name']
    readonly_fields = ['created_at', 'updated_at']

    def message_count(self, obj):
        return obj.chat_messages.count()
    message_count.short_description = 'Messages'


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['session', 'created_at', 'response_time_ms', 'is_edited']
    list_filter = ['session', 'created_at', 'is_edited']
    search_fields = ['user_message', 'assistant_response']
    readonly_fields = ['created_at', 'edited_at']


@admin.register(RAGConfig)
class RAGConfigAdmin(admin.ModelAdmin):
    list_display = ['project', 'temperature', 'top_p', 'auto_sync_enabled']
    list_filter = ['auto_sync_enabled', 'updated_at']
    search_fields = ['project__name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(FileWatchEvent)
class FileWatchEventAdmin(admin.ModelAdmin):
    list_display = ['project', 'event_type', 'file_path', 'processed', 'created_at']
    list_filter = ['event_type', 'processed', 'created_at']
    search_fields = ['file_path', 'project__name']
    readonly_fields = ['created_at', 'processed_at']
