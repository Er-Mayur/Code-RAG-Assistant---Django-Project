"""
URL Configuration for RAG app
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views_api import ProjectViewSet, ChatSessionViewSet

router = DefaultRouter()
router.register(r'projects', ProjectViewSet)
router.register(r'sessions', ChatSessionViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
