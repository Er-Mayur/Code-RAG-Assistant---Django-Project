"""
App configuration for RAG
"""
from django.apps import AppConfig


class RagConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.rag'
    verbose_name = 'RAG Assistant'

    def ready(self):
        """Initialize app"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info("RAG App initialized")
