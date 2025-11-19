"""
Models for RAG application
"""
from django.db import models
from django.utils import timezone
import json


class Project(models.Model):
    """Project model to store user projects"""
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    folder_path = models.TextField()  # Local folder path
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_indexed = models.DateTimeField(null=True, blank=True)
    total_files = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class FileIndex(models.Model):
    """Index for project files"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='files')
    file_path = models.TextField()
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50)  # .py, .js, etc.
    content_hash = models.CharField(max_length=64)  # SHA256 hash
    file_size = models.IntegerField()  # in bytes
    indexed_at = models.DateTimeField(auto_now=True)
    embedding_stored = models.BooleanField(default=False)
    chunk_count = models.IntegerField(default=0)

    class Meta:
        unique_together = ('project', 'file_path')
        ordering = ['file_name']

    def __str__(self):
        return f"{self.project.name} / {self.file_name}"


class TextChunk(models.Model):
    """Store text chunks for RAG"""
    file_index = models.ForeignKey(FileIndex, on_delete=models.CASCADE, related_name='chunks')
    chunk_index = models.IntegerField()
    content = models.TextField()
    start_line = models.IntegerField(null=True, blank=True)
    end_line = models.IntegerField(null=True, blank=True)
    embedding_vector = models.JSONField(null=True, blank=True)  # Store embedding
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('file_index', 'chunk_index')
        ordering = ['chunk_index']

    def __str__(self):
        return f"{self.file_index.file_name} - Chunk {self.chunk_index}"


class ChatSession(models.Model):
    """Chat session for each project"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='chat_sessions')
    title = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_archived = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.project.name} - {self.title or 'Untitled'}"

    def save(self, *args, **kwargs):
        if not self.title and self.chat_messages.exists():
            # Auto-generate title from first message
            first_msg = self.chat_messages.first()
            self.title = first_msg.user_message[:50] + "..."
        super().save(*args, **kwargs)


class ChatMessage(models.Model):
    """Individual chat messages"""
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    ]

    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='chat_messages')
    user_message = models.TextField()
    assistant_response = models.TextField(blank=True, null=True)
    context_files = models.JSONField(default=list, blank=True)  # List of file paths used
    context_chunks = models.JSONField(default=list, blank=True)  # Relevant chunks
    created_at = models.DateTimeField(auto_now_add=True)
    response_time_ms = models.IntegerField(null=True, blank=True)
    tokens_used = models.JSONField(default=dict, blank=True)
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Message from {self.session} at {self.created_at}"


class RAGConfig(models.Model):
    """Store RAG configuration per project"""
    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name='rag_config')
    temperature = models.FloatField(default=0.3)
    top_p = models.FloatField(default=0.9)
    max_context_tokens = models.IntegerField(default=4096)
    chunk_size = models.IntegerField(default=1000)
    chunk_overlap = models.IntegerField(default=100)
    similarity_threshold = models.FloatField(default=0.25)
    auto_sync_enabled = models.BooleanField(default=True)
    sync_interval_minutes = models.IntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"RAG Config for {self.project.name}"


class FileWatchEvent(models.Model):
    """Track file changes for auto-sync"""
    EVENT_TYPES = [
        ('created', 'Created'),
        ('modified', 'Modified'),
        ('deleted', 'Deleted'),
        ('moved', 'Moved'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='watch_events')
    file_path = models.TextField()
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.project.name} - {self.event_type} - {self.file_path}"
