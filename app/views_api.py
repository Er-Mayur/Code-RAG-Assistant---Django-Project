"""
API Views for RAG app
"""
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.utils import timezone
from .models import Project, ChatSession, ChatMessage, FileIndex, RAGConfig
from .serializers import (ProjectSerializer, ChatSessionSerializer, ChatMessageSerializer,
                          ChatSessionListSerializer)
from .rag_utils import FileScanner, TextChunker
from .ollama_service import OllamaService
import time

logger = logging.getLogger(__name__)
ollama = OllamaService()


class ProjectViewSet(viewsets.ModelViewSet):
    """ViewSet for Project management"""
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [AllowAny]

    @action(detail=False, methods=['post'])
    def create_project(self, request):
        """Create new project from folder path"""
        folder_path = request.data.get('folder_path')
        name = request.data.get('name')
        description = request.data.get('description', '')

        if not folder_path or not name:
            return Response({'error': 'folder_path and name required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Create project
            project = Project.objects.create(
                name=name,
                description=description,
                folder_path=folder_path,
                last_indexed=timezone.now()
            )

            # Create default RAG config
            RAGConfig.objects.create(project=project)

            # Create default chat session
            default_session = ChatSession.objects.create(
                project=project,
                title=f"Chat with {name}"
            )

            # Index files
            self._index_project_files(project)

            serializer = ProjectSerializer(project)
            response_data = serializer.data
            response_data['chat_session_id'] = default_session.id
            return Response(response_data, status=status.HTTP_201_CREATED)
        except FileNotFoundError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error creating project: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def reindex_files(self, request, pk=None):
        """Re-index all files in project"""
        project = self.get_object()
        try:
            self._index_project_files(project)
            serializer = ProjectSerializer(project)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error reindexing project: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def get_files(self, request, pk=None):
        """Get all files in project"""
        project = self.get_object()
        files = project.files.all()
        serializer = ProjectSerializer(project)
        return Response({
            'project': serializer.data,
            'files_count': files.count(),
            'files': FileIndex.objects.filter(project=project).values(
                'id', 'file_name', 'file_path', 'file_type', 'file_size', 'chunk_count'
            )
        })

    @action(detail=False, methods=['get'])
    def check_ollama(self, request):
        """Check if Ollama is available"""
        is_available = ollama.is_available()
        available_models = ollama.get_available_models() if is_available else []
        return Response({
            'available': is_available,
            'models': available_models,
            'configured_model': ollama.model
        })

    @action(detail=True, methods=['post'])
    def delete_project(self, request, pk=None):
        """Delete project and all associated data (chat sessions, messages, files, chunks)"""
        try:
            project = self.get_object()
            project_name = project.name
            
            # Delete all chat sessions (which will cascade delete messages)
            # Delete all files (which will cascade delete chunks)
            project.chat_sessions.all().delete()
            project.files.all().delete()
            
            # Delete the project itself
            project.delete()
            
            logger.info(f"Project '{project_name}' deleted successfully with all associated data")
            return Response({'success': True, 'message': f'Project {project_name} deleted successfully'}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error deleting project: {str(e)}")
            return Response({'error': str(e), 'success': False}, status=status.HTTP_400_BAD_REQUEST)

    def _index_project_files(self, project: Project):
        """Index all files in project folder"""
        scanner = FileScanner()
        chunker = TextChunker()

        # Get files from folder
        files = scanner.get_files_from_folder(project.folder_path)

        # Clear old files
        project.files.all().delete()

        file_count = 0
        for file_info in files:
            try:
                # Read file content
                content = scanner.read_file_content(file_info['full_path'])

                # Create FileIndex entry
                file_index = FileIndex.objects.create(
                    project=project,
                    file_path=file_info['relative_path'],
                    file_name=file_info['name'],
                    file_type=file_info['extension'],
                    content_hash=file_info['hash'],
                    file_size=file_info['size']
                )

                # Chunk and store text
                chunks = chunker.chunk_text(content, file_info['extension'])
                for idx, (chunk_text, start_line, end_line) in enumerate(chunks):
                    # In production, generate and store embeddings here
                    from .models import TextChunk
                    TextChunk.objects.create(
                        file_index=file_index,
                        chunk_index=idx,
                        content=chunk_text,
                        start_line=start_line,
                        end_line=end_line
                    )

                file_index.chunk_count = len(chunks)
                file_index.embedding_stored = True
                file_index.save()

                file_count += 1
            except Exception as e:
                logger.error(f"Error indexing file {file_info['name']}: {str(e)}")
                continue

        project.total_files = file_count
        project.last_indexed = timezone.now()
        project.save()


class ChatSessionViewSet(viewsets.ModelViewSet):
    """ViewSet for Chat Sessions"""
    queryset = ChatSession.objects.all()
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action == 'list':
            return ChatSessionListSerializer
        return ChatSessionSerializer

    def get_queryset(self):
        project_id = self.request.query_params.get('project_id')
        if project_id:
            return ChatSession.objects.filter(project_id=project_id)
        return ChatSession.objects.all()

    @action(detail=False, methods=['post'])
    def create_session(self, request):
        """Create new chat session"""
        project_id = request.data.get('project_id')
        title = request.data.get('title', '')

        if not project_id:
            return Response({'error': 'project_id required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            project = Project.objects.get(id=project_id)
            session = ChatSession.objects.create(project=project, title=title)
            serializer = ChatSessionSerializer(session)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Project.DoesNotExist:
            return Response({'error': 'Project not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        """Send message and get response"""
        session = self.get_object()
        user_message = request.data.get('message', '').strip()

        if not user_message:
            return Response({'error': 'Message cannot be empty'}, status=status.HTTP_400_BAD_REQUEST)

        start_time = time.time()

        try:
            # Get relevant context from project files
            context_chunks = self._get_context_for_query(session.project, user_message)
            logger.info(f"Found {len(context_chunks)} context chunks for query")

            # Generate response
            response_text = ollama.chat_with_context(
                user_message,
                [chunk['text'] for chunk in context_chunks],
                temperature=session.project.rag_config.temperature if hasattr(session.project, 'rag_config') else 0.3
            )

            logger.info(f"Response generated: {response_text[:100]}")

            # Save message
            message = ChatMessage.objects.create(
                session=session,
                user_message=user_message,
                assistant_response=response_text,
                context_files=[c['file'] for c in context_chunks],
                context_chunks=[c['text'][:200] for c in context_chunks],
                response_time_ms=int((time.time() - start_time) * 1000)
            )

            serializer = ChatMessageSerializer(message)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}", exc_info=True)
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def _get_context_for_query(self, project: Project, query: str, top_k: int = 5):
        """Get relevant context chunks for query using semantic search"""
        from .models import TextChunk
        from .ollama_service import OllamaService
        import numpy as np

        try:
            # Get query embedding
            ollama_svc = OllamaService()
            query_embedding = ollama_svc.get_embedding(query)
            
            if not query_embedding:
                logger.warning("Failed to get query embedding, falling back to keyword search")
                return self._get_context_by_keywords(project, query, top_k)
            
            query_embedding = np.array(query_embedding)
            similarity_threshold = project.rag_config.similarity_threshold if hasattr(project, 'rag_config') else 0.3
            
            # Get all chunks for this project
            all_chunks = TextChunk.objects.filter(
                file_index__project=project
            ).values('id', 'content', 'file_index__file_name', 'start_line', 'end_line')
            
            results = []
            for chunk in all_chunks:
                try:
                    # Get embedding for chunk
                    chunk_embedding = ollama_svc.get_embedding(chunk['content'][:500])  # Use first 500 chars for speed
                    
                    if chunk_embedding:
                        chunk_embedding = np.array(chunk_embedding)
                        
                        # Calculate cosine similarity
                        dot_product = np.dot(query_embedding, chunk_embedding)
                        magnitude_q = np.linalg.norm(query_embedding)
                        magnitude_c = np.linalg.norm(chunk_embedding)
                        
                        if magnitude_q > 0 and magnitude_c > 0:
                            similarity = dot_product / (magnitude_q * magnitude_c)
                            
                            if similarity > similarity_threshold:
                                results.append({
                                    'text': chunk['content'],
                                    'file': chunk['file_index__file_name'],
                                    'start_line': chunk['start_line'],
                                    'end_line': chunk['end_line'],
                                    'score': float(similarity)
                                })
                except Exception as e:
                    logger.warning(f"Error processing chunk {chunk['id']}: {str(e)}")
                    continue
            
            # Sort by similarity and return top_k
            results.sort(key=lambda x: x['score'], reverse=True)
            logger.info(f"Semantic search found {len(results)} relevant chunks, returning top {min(len(results), top_k)}")
            return results[:top_k]
            
        except Exception as e:
            logger.error(f"Error in semantic search: {str(e)}", exc_info=True)
            logger.info("Falling back to keyword search")
            return self._get_context_by_keywords(project, query, top_k)
    
    def _get_context_by_keywords(self, project: Project, query: str, top_k: int = 5):
        """Fallback: Get relevant context by keyword matching"""
        from .models import TextChunk
        import re
        
        keywords = set(re.findall(r'\b\w+\b', query.lower()))
        chunks = TextChunk.objects.filter(
            file_index__project=project
        ).values('content', 'file_index__file_name', 'start_line', 'end_line').distinct()[:top_k*2]
        
        results = []
        for chunk in chunks:
            score = sum(1 for kw in keywords if kw in chunk['content'].lower())
            if score > 0:
                results.append({
                    'text': chunk['content'],
                    'file': chunk['file_index__file_name'],
                    'start_line': chunk['start_line'],
                    'end_line': chunk['end_line'],
                    'score': score
                })
        
        logger.info(f"Keyword search found {len(results)} relevant chunks")
        return sorted(results, key=lambda x: x['score'], reverse=True)[:top_k]

    @action(detail=True, methods=['get'])
    def get_messages(self, request, pk=None):
        """Get all messages in session"""
        session = self.get_object()
        messages = session.chat_messages.all()
        serializer = ChatMessageSerializer(messages, many=True)
        return Response(serializer.data)
