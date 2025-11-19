"""
Frontend views for RAG app
"""
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from .models import Project, ChatSession
from django.urls import path


def index(request):
    """Home page"""
    projects = Project.objects.filter(is_active=True).order_by('-updated_at')
    context = {
        'projects': projects,
        'page': 'home'
    }
    return render(request, 'index.html', context)


def project_detail(request, project_id):
    """Project detail page"""
    try:
        project = Project.objects.get(id=project_id)
        sessions = project.chat_sessions.filter(is_archived=False).order_by('-updated_at')
        context = {
            'project': project,
            'sessions': sessions,
            'page': 'project'
        }
        return render(request, 'project.html', context)
    except Project.DoesNotExist:
        return redirect('index')


def chat_session(request, session_id):
    """Chat session page"""
    try:
        session = ChatSession.objects.get(id=session_id)
        messages = session.chat_messages.all().order_by('created_at')
        context = {
            'session': session,
            'project': session.project,
            'messages': messages,
            'page': 'chat'
        }
        return render(request, 'chat.html', context)
    except ChatSession.DoesNotExist:
        return redirect('index')


# URL patterns for views
urlpatterns = [
    path('', index, name='index'),
    path('project/<int:project_id>/', project_detail, name='project_detail'),
    path('chat/<int:session_id>/', chat_session, name='chat_session'),
]
