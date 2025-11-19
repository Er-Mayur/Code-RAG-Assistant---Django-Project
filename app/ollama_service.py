"""
Ollama integration for RAG queries
"""
import requests
import json
import logging
from typing import List, Dict, Generator
from django.conf import settings
import time

logger = logging.getLogger(__name__)


class OllamaService:
    """Service to interact with Ollama API"""

    def __init__(self):
        self.base_url = settings.RAG_CONFIG['OLLAMA_BASE_URL']
        self.model = settings.RAG_CONFIG['MODEL_NAME']
        self.embedding_model = settings.RAG_CONFIG['EMBEDDING_MODEL']
        self.timeout = 300  # 5 minutes

    def is_available(self) -> bool:
        """Check if Ollama is running"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama not available: {str(e)}")
            return False

    def pull_model(self, model_name: str = None) -> bool:
        """Pull model from ollama registry"""
        model = model_name or self.model
        try:
            response = requests.post(
                f"{self.base_url}/api/pull",
                json={"name": model},
                timeout=self.timeout,
                stream=True
            )
            if response.status_code == 200:
                logger.info(f"Model {model} pulled successfully")
                return True
            return False
        except Exception as e:
            logger.error(f"Error pulling model: {str(e)}")
            return False

    def get_embedding(self, text: str) -> List[float]:
        """Get embedding vector for text"""
        try:
            response = requests.post(
                f"{self.base_url}/api/embeddings",
                json={
                    "model": self.embedding_model,
                    "prompt": text
                },
                timeout=self.timeout
            )
            if response.status_code == 200:
                data = response.json()
                return data.get('embedding', [])
            return []
        except Exception as e:
            logger.error(f"Error getting embedding: {str(e)}")
            return []

    def generate_response(self, prompt: str, context: str = "", **kwargs) -> str:
        """Generate response from model (non-streaming)"""
        full_prompt = self._build_prompt(prompt, context)

        try:
            logger.info(f"Sending request to {self.base_url}/api/generate with model {self.model}")
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": full_prompt,
                    "stream": False,
                    "temperature": kwargs.get('temperature', settings.RAG_CONFIG['TEMPERATURE']),
                    "top_p": kwargs.get('top_p', settings.RAG_CONFIG['TOP_P']),
                },
                timeout=self.timeout
            )

            logger.info(f"Response status code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                result = data.get('response', '')
                logger.info(f"Generated response length: {len(result)}")
                return result
            else:
                error_msg = f"Error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return error_msg
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}", exc_info=True)
            return f"Error: {str(e)}"

    def generate_response_stream(self, prompt: str, context: str = "", **kwargs) -> Generator[str, None, None]:
        """Generate response from model (streaming)"""
        full_prompt = self._build_prompt(prompt, context)

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": full_prompt,
                    "stream": True,
                    "temperature": kwargs.get('temperature', settings.RAG_CONFIG['TEMPERATURE']),
                    "top_p": kwargs.get('top_p', settings.RAG_CONFIG['TOP_P']),
                },
                timeout=self.timeout,
                stream=True
            )

            if response.status_code == 200:
                for line in response.iter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            yield data.get('response', '')
                        except json.JSONDecodeError:
                            continue
            else:
                yield f"Error: {response.status_code}"
        except Exception as e:
            logger.error(f"Error generating response stream: {str(e)}")
            yield f"Error: {str(e)}"

    def _build_prompt(self, user_prompt: str, context: str = "") -> str:
        """Build prompt with context"""
        if context:
            prompt = f"""You are a helpful coding assistant. Use the provided code context to answer questions accurately.

Context from project files:
{context}

---

User Question: {user_prompt}

Please provide a helpful response based on the context above. If the context doesn't contain relevant information, say so clearly."""
        else:
            prompt = f"""You are a helpful coding assistant. Answer the following question:

{user_prompt}

Provide a clear and concise response."""

        return prompt

    def chat_with_context(self, user_message: str, context_chunks: List[str] = None, **kwargs) -> str:
        """Chat with context chunks"""
        context = ""
        if context_chunks:
            context = "\n\n---\n\n".join(context_chunks[:5])  # Limit to 5 chunks

        return self.generate_response(user_message, context, **kwargs)

    def get_available_models(self) -> List[str]:
        """Get list of available models"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [model['name'] for model in data.get('models', [])]
            return []
        except Exception as e:
            logger.error(f"Error getting models: {str(e)}")
            return []


class VectorStore:
    """Simple in-memory vector store (can be replaced with ChromaDB later)"""

    def __init__(self):
        self.embeddings = {}
        self.ollama = OllamaService()

    def add_embedding(self, chunk_id: str, text: str, embedding: List[float] = None):
        """Add embedding for a chunk"""
        if embedding is None:
            embedding = self.ollama.get_embedding(text)

        self.embeddings[chunk_id] = {
            'text': text,
            'embedding': embedding,
        }

    def search_similar(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search for similar chunks"""
        query_embedding = self.ollama.get_embedding(query)
        if not query_embedding:
            return []

        # Calculate similarity scores
        results = []
        for chunk_id, data in self.embeddings.items():
            similarity = self._cosine_similarity(query_embedding, data['embedding'])
            if similarity > settings.RAG_CONFIG.get('SIMILARITY_THRESHOLD', 0.5):
                results.append({
                    'chunk_id': chunk_id,
                    'text': data['text'],
                    'similarity': similarity
                })

        # Sort by similarity and return top_k
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results[:top_k]

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        if not a or not b or len(a) != len(b):
            return 0.0

        dot_product = sum(x * y for x, y in zip(a, b))
        magnitude_a = sum(x ** 2 for x in a) ** 0.5
        magnitude_b = sum(x ** 2 for x in b) ** 0.5

        if magnitude_a == 0 or magnitude_b == 0:
            return 0.0

        return dot_product / (magnitude_a * magnitude_b)
