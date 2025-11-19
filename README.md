# 🧠 Code RAG Assistant - Django Project

A personalized AI-powered code assistant that uses **Retrieval-Augmented Generation (RAG)** with **Ollama** and **deepseek-coder** model to provide intelligent code analysis, debugging, and assistance for your projects.

## Features

✨ **Key Capabilities:**
- **Local Project Indexing**: Scan and index all code files from your project folders
- **Persistent Knowledge Base**: Each project has its own separate RAG knowledge base
- **Real-time Chat Interface**: ChatGPT-like interface with streaming responses
- **Auto-Sync**: Automatically update project files when they change on disk
- **Chat History**: Full conversation history maintained per project
- **Context-Aware Responses**: AI uses relevant code context for accurate answers
- **Offline Processing**: Everything runs locally with Ollama - no cloud data sent
- **Beautiful Dashboard**: Modern, responsive UI inspired by ChatGPT

## 🖼️ UI Screenshots

### ➕ Add New Project Modal
![Add Project Screenshot](attachment:/mnt/data/Screenshot 2025-11-19 at 6.25.26 PM.png)

---

### 📁 Project Overview Page  
![Project Overview Screenshot](attachment:/mnt/data/Screenshot 2025-11-19 at 6.27.29 PM.png)

---

### 💬 Chat Interface  
![Chat Interface Screenshot](attachment:/mnt/data/Screenshot 2025-11-19 at 6.28.27 PM.png)


## Tech Stack

- **Backend**: Django 4.2 + Django REST Framework + Channels (WebSockets)
- **Frontend**: HTML/CSS/JavaScript with real-time updates
- **AI Model**: Ollama + deepseek-coder:6.7b
- **Database**: SQLite (easily switch to PostgreSQL)
- **Server**: Daphne (ASGI) for WebSocket support

## Prerequisites

Before setup, make sure you have:

1. **Python 3.10+** installed
2. **Ollama** installed and running ([Download Ollama](https://ollama.ai))
3. **deepseek-coder model** pulled in Ollama
4. **Git** (optional, for version control)

### Install Ollama

```bash
# Download from https://ollama.ai
# After installation, pull the model:
ollama pull deepseek-coder:6.7b
ollama pull nomic-embed-text

# Start Ollama (runs on http://localhost:11434)
ollama serve
```

## Installation & Setup

### 1. Create Virtual Environment

```bash
cd /Users/mayur/Projects/Codes/Python/Django/RAGProject

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run Migrations

```bash
python manage.py migrate
```

### 4. Create Admin User (Optional)

```bash
python manage.py createsuperuser
```

### 5. Run Development Server

```bash
# With ASGI (for WebSocket support)
python manage.py runserver 0.0.0.0:8000

# Or use Daphne directly for better WebSocket support:
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

### 6. Access the Application

Open your browser and navigate to:
```
http://localhost:8000
```

## Usage Guide

### Adding a Project

1. Click **"+ Add Project"** button on the home page
2. Enter:
   - **Project Name**: Your project's name
   - **Folder Path**: Absolute path to your project folder (e.g., `/Users/username/projects/my-app`)
   - **Description**: Optional project description
3. Click **"Create Project"**
4. Wait for files to be indexed (progress shown on project page)

### Starting a Chat

1. Navigate to a project from the home page
2. Click **"+ New Chat"** to start a new conversation
3. Ask questions about your code:
   - "What does the authentication module do?"
   - "Find bugs in the payment processing code"
   - "Explain how the database connection works"
   - "Fix this error: [paste error message]"

### Reindexing Files

When you make changes to your project files:

1. Go to the project page
2. Click **"🔄 Reindex"** button
3. The RAG system will scan and update the knowledge base

## File Structure

```
RAGProject/
├── config/                          # Django configuration
│   ├── settings.py                 # Main settings
│   ├── urls.py                     # URL routing
│   ├── asgi.py                     # ASGI configuration
│   └── wsgi.py                     # WSGI configuration
├── app/                            # Main RAG application
│   ├── models.py                   # Database models
│   ├── views.py                    # Frontend views
│   ├── views_api.py                # REST API views
│   ├── serializers.py              # DRF serializers
│   ├── consumers.py                # WebSocket consumers
│   ├── routing.py                  # WebSocket routing
│   ├── urls.py                     # API URLs
│   ├── rag_utils.py                # File scanning & chunking
│   ├── ollama_service.py           # Ollama integration
│   └── migrations/                 # Database migrations
|
├── templates/                      # HTML templates
│   ├── base.html                   # Base template
│   ├── index.html                  # Projects page
│   ├── project.html                # Project detail page
│   └── chat.html                   # Chat interface
├── static/                         # Static files (CSS, JS, images)
├── manage.py                       # Django management script
├── requirements.txt                # Python dependencies
└── README.md                       # This file
```

## Database Models

### Project
- Stores project metadata
- Links to files and chat sessions
- Tracks indexing status

### FileIndex
- Records indexed files
- Stores content hash for change detection
- Tracks chunk count

### TextChunk
- Individual text chunks for RAG
- Stores embeddings
- Links to source file

### ChatSession
- Groups related messages
- Belongs to a project
- Auto-titles based on first message

### ChatMessage
- Individual chat messages
- Stores both user and AI responses
- Tracks context files used
- Records response time

## API Endpoints

### Projects API
```
POST   /api/projects/                 # List/create projects
GET    /api/projects/{id}/            # Get project details
POST   /api/projects/create_project/  # Create new project
POST   /api/projects/{id}/reindex_files/  # Reindex project files
GET    /api/projects/{id}/get_files/  # List project files
GET    /api/projects/check_ollama/    # Check Ollama status
```

### Chat Sessions API
```
GET    /api/sessions/                 # List sessions
POST   /api/sessions/create_session/  # Create new chat session
POST   /api/sessions/{id}/send_message/  # Send chat message
GET    /api/sessions/{id}/get_messages/  # Get session messages
```

### WebSocket
```
ws://localhost:8000/ws/chat/{session_id}/
```

## Configuration

Edit `config/settings.py` to customize:

### RAG Configuration
```python
RAG_CONFIG = {
    'OLLAMA_BASE_URL': 'http://localhost:11434',
    'MODEL_NAME': 'deepseek-coder:6.7b',
    'EMBEDDING_MODEL': 'nomic-embed-text',
    'CHUNK_SIZE': 1000,           # Characters per chunk
    'CHUNK_OVERLAP': 100,         # Overlap between chunks
    'MAX_CONTEXT_LENGTH': 4096,   # Max context tokens
    'TEMPERATURE': 0.3,           # 0.0-1.0 (lower = more deterministic)
    'TOP_P': 0.9,                 # Nucleus sampling
}
```

### File Indexing
```python
FILE_WATCH_EXTENSIONS = ['.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.go', '.rs', '.rb', '.php', '.cs', '.scala']
MAX_FILES_PER_PROJECT = 1000
MAX_FILE_SIZE_MB = 10
```

## Troubleshooting

### Ollama Not Connecting
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not running, start Ollama:
ollama serve

# Pull model if needed:
ollama pull deepseek-coder:6.7b
```

### WebSocket Connection Issues
- Ensure you're using `daphne` for WebSocket support
- Check browser console for errors
- Falls back to HTTP polling if WebSocket fails

### Files Not Indexing
1. Check file paths are correct
2. Ensure files have allowed extensions
3. Check file size limits (default 10MB)
4. Look at Django logs for errors

### Slow Response
- Reduce `CHUNK_SIZE` for faster processing
- Reduce number of context chunks used
- Ensure Ollama server is running locally
- Check available RAM/CPU

## Advanced Features (Future Enhancement)

These can be added to extend functionality:

1. **Embedding Storage**: Use ChromaDB/Weaviate for persistent embeddings
2. **Advanced RAG**: Implement hybrid search (BM25 + semantic)
3. **Multi-Language Support**: Add support for more programming languages
4. **Code Execution**: Safe sandbox for running code suggestions
5. **Integration**: GitHub/GitLab integration for auto-sync
6. **Cloud Deployment**: Docker + cloud hosting setup
7. **Team Collaboration**: Multi-user support with access control
8. **Custom Models**: Support for different Ollama models

## Performance Tips

1. **Batch Indexing**: Index in background for large projects
2. **Caching**: Implement Redis caching for frequent queries
3. **Async Tasks**: Use Celery for background file watching
4. **Database Indexing**: Add database indices for frequently queried columns
5. **Vector Caching**: Cache embeddings in ChromaDB

## Deployment

### Docker Setup (Optional)
Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
```

Build and run:
```bash
docker build -t rag-assistant .
docker run -p 8000:8000 -v /path/to/projects:/projects rag-assistant
```

## License

MIT License - Feel free to use and modify!

## Support

For issues or questions:
1. Check Django/DRF documentation
2. Review Ollama documentation
3. Check browser console for frontend errors
4. Enable DEBUG=True in settings for detailed errors

## Contributing

Contributions welcome! Areas for improvement:
- Better embedding/vector search
- Multi-language syntax highlighting
- Real-time file watching with watchdog
- Performance optimizations
- UI/UX enhancements

---

**Happy coding! 🚀**

For latest updates and features, check the repository README.
