"""
Serializers for RAG app
"""
from rest_framework import serializers
from .models import Project, FileIndex, ChatSession, ChatMessage, RAGConfig


class RAGConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = RAGConfig
        fields = '__all__'


class FileIndexSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileIndex
        fields = ['id', 'file_path', 'file_name', 'file_type', 'file_size', 'indexed_at', 'chunk_count']
        read_only_fields = ['id', 'indexed_at']


class ProjectSerializer(serializers.ModelSerializer):
    files = FileIndexSerializer(many=True, read_only=True)
    rag_config = RAGConfigSerializer(read_only=True)

    class Meta:
        model = Project
        fields = ['id', 'name', 'description', 'folder_path', 'created_at', 'updated_at',
                  'last_indexed', 'total_files', 'is_active', 'files', 'rag_config']
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_indexed', 'total_files']


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['id', 'user_message', 'assistant_response', 'context_files', 'context_chunks',
                  'created_at', 'response_time_ms', 'tokens_used', 'is_edited']
        read_only_fields = ['id', 'created_at', 'assistant_response', 'context_files', 'context_chunks']


class ChatSessionSerializer(serializers.ModelSerializer):
    chat_messages = ChatMessageSerializer(many=True, read_only=True)

    class Meta:
        model = ChatSession
        fields = ['id', 'project', 'title', 'created_at', 'updated_at', 'is_archived', 'chat_messages']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ChatSessionListSerializer(serializers.ModelSerializer):
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = ChatSession
        fields = ['id', 'project', 'title', 'created_at', 'updated_at', 'is_archived', 'message_count']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_message_count(self, obj):
        return obj.chat_messages.count()
