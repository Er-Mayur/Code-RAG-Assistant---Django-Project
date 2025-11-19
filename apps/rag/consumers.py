"""
WebSocket consumers for real-time chat
"""
import json
import asyncio
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from .models import ChatSession, ChatMessage
from .ollama_service import OllamaService

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time chat"""

    async def connect(self):
        """Handle WebSocket connection"""
        self.session_id = self.scope['url_route']['kwargs']['session_id']
        self.session_group_name = f'chat_{self.session_id}'

        # Join session group
        await self.channel_layer.group_add(
            self.session_group_name,
            self.channel_name
        )

        await self.accept()

        # Verify session exists
        session = await self.get_session()
        if session:
            await self.send(json.dumps({
                'type': 'connection',
                'status': 'connected',
                'session_id': self.session_id
            }))
        else:
            await self.close()

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        # Remove group - we're not using group_send anymore for direct 1-to-1
        await self.channel_layer.group_discard(
            self.session_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """Handle incoming message"""
        try:
            data = json.loads(text_data)
            message_text = data.get('message', '').strip()

            if not message_text:
                await self.send(json.dumps({
                    'type': 'error',
                    'message': 'Message cannot be empty'
                }))
                return

            # Notify that AI is thinking
            await self.send(json.dumps({
                'type': 'thinking'
            }))

            # Generate AI response
            await self.generate_response(message_text)

        except json.JSONDecodeError:
            await self.send(json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))
        except Exception as e:
            logger.error(f"Error in receive: {str(e)}")
            await self.send(json.dumps({
                'type': 'error',
                'message': str(e)
            }))

    async def generate_response(self, user_message):
        """Generate AI response"""
        try:
            session = await self.get_session()
            if not session:
                await self.send(json.dumps({
                    'type': 'error',
                    'message': 'Session not found'
                }))
                return

            # Get context and generate response in thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                self._get_ai_response,
                session,
                user_message
            )

            # Send response directly to client
            await self.send(json.dumps({
                'type': 'ai_response',
                'response': response['text'],
                'context_files': response['context_files']
            }))

            # Save message to database
            await self.save_message(user_message, response['text'], response['context_files'])

        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            await self.send(json.dumps({
                'type': 'error',
                'message': f"Error: {str(e)}"
            }))

    def _get_ai_response(self, session, user_message):
        """Get AI response (runs in thread pool)"""
        try:
            ollama = OllamaService()

            # Get context
            from .views_api import ChatSessionViewSet
            viewset = ChatSessionViewSet()
            context_chunks = viewset._get_context_for_query(session.project, user_message, top_k=5)

            # Generate response
            response_text = ollama.chat_with_context(
                user_message,
                [chunk['text'] for chunk in context_chunks],
            )

            return {
                'text': response_text,
                'context_files': [c['file'] for c in context_chunks]
            }
        except Exception as e:
            logger.error(f"Error in _get_ai_response: {str(e)}")
            return {
                'text': f"Error: {str(e)}",
                'context_files': []
            }

    @sync_to_async
    def get_session(self):
        """Get chat session from database"""
        try:
            return ChatSession.objects.get(id=self.session_id)
        except ChatSession.DoesNotExist:
            return None

    @sync_to_async
    def save_message(self, user_message, response_text, context_files):
        """Save message to database"""
        try:
            session = ChatSession.objects.get(id=self.session_id)
            ChatMessage.objects.create(
                session=session,
                user_message=user_message,
                assistant_response=response_text,
                context_files=context_files
            )
        except Exception as e:
            logger.error(f"Error saving message: {str(e)}")
