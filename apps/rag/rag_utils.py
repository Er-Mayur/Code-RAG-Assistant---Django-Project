"""
RAG utilities for file scanning and indexing
"""
import os
import hashlib
import mimetypes
from pathlib import Path
from django.conf import settings
from typing import List, Dict, Tuple


class FileScanner:
    """Scan project folders and extract files"""

    ALLOWED_EXTENSIONS = settings.FILE_WATCH_EXTENSIONS
    EXCLUDED_EXTENSIONS = getattr(settings, 'EXCLUDED_EXTENSIONS', [])
    MAX_FILES = settings.MAX_FILES_PER_PROJECT
    MAX_FILE_SIZE = settings.MAX_FILE_SIZE_MB * 1024 * 1024

    @staticmethod
    def get_file_hash(file_path: str) -> str:
        """Calculate SHA256 hash of file content"""
        sha256_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for byte_block in iter(lambda: f.read(4096), b''):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    @staticmethod
    def is_file_allowed(filename: str) -> bool:
        """Check if file should be indexed"""
        _, ext = os.path.splitext(filename)
        ext_lower = ext.lower()
        
        # If ALLOWED_EXTENSIONS is None, allow all except excluded
        if FileScanner.ALLOWED_EXTENSIONS is None:
            # Check if extension is excluded
            if ext_lower in [e.lower() for e in FileScanner.EXCLUDED_EXTENSIONS]:
                return False
            # Check if filename is in excluded (for node_modules, etc)
            if filename.lower() in [e.lower() for e in FileScanner.EXCLUDED_EXTENSIONS]:
                return False
            return True
        else:
            # Use whitelist if provided
            return ext_lower in [e.lower() for e in FileScanner.ALLOWED_EXTENSIONS]

    @staticmethod
    def get_files_from_folder(folder_path: str) -> List[Dict[str, any]]:
        """Get all indexable files from folder"""
        files = []
        count = 0

        if not os.path.exists(folder_path):
            raise FileNotFoundError(f"Folder not found: {folder_path}")

        for root, dirs, filenames in os.walk(folder_path):
            # Skip hidden directories and common ones
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules', 'venv', '.venv']]

            for filename in filenames:
                if count >= FileScanner.MAX_FILES:
                    break

                file_path = os.path.join(root, filename)

                # Check if file should be indexed
                if not FileScanner.is_file_allowed(filename):
                    continue

                # Check file size
                try:
                    file_size = os.path.getsize(file_path)
                    if file_size > FileScanner.MAX_FILE_SIZE:
                        continue

                    files.append({
                        'full_path': file_path,
                        'relative_path': os.path.relpath(file_path, folder_path),
                        'name': filename,
                        'extension': os.path.splitext(filename)[1],
                        'size': file_size,
                        'hash': FileScanner.get_file_hash(file_path)
                    })
                    count += 1
                except (OSError, IOError):
                    continue

            if count >= FileScanner.MAX_FILES:
                break

        return files

    @staticmethod
    def read_file_content(file_path: str) -> str:
        """Read file content safely"""
        try:
            # Special handling for Jupyter notebooks
            if file_path.endswith('.ipynb'):
                return FileScanner.extract_from_notebook(file_path)
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {str(e)}"

    @staticmethod
    def extract_from_notebook(file_path: str) -> str:
        """Extract code and markdown from Jupyter notebook"""
        import json
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                notebook = json.load(f)
            
            content = []
            
            # Extract cells
            if 'cells' in notebook:
                for cell in notebook['cells']:
                    cell_type = cell.get('cell_type', 'code')
                    source = cell.get('source', [])
                    
                    if isinstance(source, list):
                        source = ''.join(source)
                    
                    if source.strip():
                        if cell_type == 'code':
                            content.append(f"# CODE CELL\n{source}")
                        elif cell_type == 'markdown':
                            content.append(f"# MARKDOWN\n{source}")
            
            # Extract metadata
            if 'metadata' in notebook:
                metadata = notebook.get('metadata', {})
                if metadata:
                    content.append(f"\n# METADATA\n# {json.dumps(metadata, indent=2)}")
            
            return '\n\n'.join(content) if content else "# Empty notebook"
        except Exception as e:
            return f"# Error reading notebook: {str(e)}"


class TextChunker:
    """Split text into chunks for embedding"""

    def __init__(self, chunk_size: int = None, overlap: int = None):
        self.chunk_size = chunk_size or settings.RAG_CONFIG['CHUNK_SIZE']
        self.chunk_overlap = overlap or settings.RAG_CONFIG['CHUNK_OVERLAP']

    def chunk_text(self, text: str, file_type: str = '.py') -> List[Tuple[str, int, int]]:
        """
        Split text into chunks with overlap
        Returns: List of (chunk_text, start_line, end_line)
        """
        chunks = []

        if file_type in ['.py', '.js', '.ts', '.java', '.cpp', '.go', '.rb']:
            # For code files, try to split by functions/classes
            chunks = self._chunk_by_semantic_units(text, file_type)
        else:
            # For other files, split by sentences
            chunks = self._chunk_by_sentences(text)

        if not chunks:
            # Fallback to simple chunking
            chunks = self._chunk_by_size(text)

        return chunks

    def _chunk_by_sentences(self, text: str) -> List[Tuple[str, int, int]]:
        """Split text by sentences"""
        sentences = text.split('. ')
        chunks = []
        current_chunk = ""
        start_line = 0

        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if len(current_chunk) + len(sentence) < self.chunk_size:
                current_chunk += sentence + ". "
            else:
                if current_chunk:
                    chunks.append((current_chunk.strip(), start_line, i))
                    start_line = i
                current_chunk = sentence + ". "

        if current_chunk:
            chunks.append((current_chunk.strip(), start_line, len(sentences)))

        return chunks

    def _chunk_by_size(self, text: str) -> List[Tuple[str, int, int]]:
        """Split text by character size with overlap"""
        chunks = []
        start = 0
        lines = text.split('\n')
        current_chunk = ""
        start_line = 0

        for i, line in enumerate(lines):
            if len(current_chunk) + len(line) < self.chunk_size:
                current_chunk += line + "\n"
            else:
                if current_chunk:
                    chunks.append((current_chunk.strip(), start_line, i))
                    start_line = max(0, i - int(self.chunk_overlap / 10))
                current_chunk = line + "\n"

        if current_chunk:
            chunks.append((current_chunk.strip(), start_line, len(lines)))

        return chunks

    def _chunk_by_semantic_units(self, text: str, file_type: str) -> List[Tuple[str, int, int]]:
        """Try to split by semantic units (functions, classes, etc)"""
        # This is a simplified approach
        # In production, use AST parsing for better results
        chunks = []
        lines = text.split('\n')
        current_chunk = []
        start_line = 0

        for i, line in enumerate(lines):
            current_chunk.append(line)

            # Check if we reached a good split point
            if (len('\n'.join(current_chunk)) >= self.chunk_size or
                    self._is_split_point(line, file_type)):
                if current_chunk:
                    chunk_text = '\n'.join(current_chunk)
                    if len(chunk_text.strip()) > 50:  # Don't add tiny chunks
                        chunks.append((chunk_text.strip(), start_line, i))
                    start_line = i
                    current_chunk = []

        if current_chunk:
            chunk_text = '\n'.join(current_chunk)
            if len(chunk_text.strip()) > 50:
                chunks.append((chunk_text.strip(), start_line, len(lines)))

        return chunks if chunks else self._chunk_by_size(text)

    @staticmethod
    def _is_split_point(line: str, file_type: str) -> bool:
        """Check if line is a good split point"""
        line = line.strip()
        if file_type in ['.py']:
            return line.startswith('def ') or line.startswith('class ')
        elif file_type in ['.js', '.ts']:
            return line.startswith('function ') or line.startswith('export ')
        elif file_type == '.java':
            return line.startswith('public ') or line.startswith('private ')
        return False
