"""
Optimized document parsing for large files with lazy loading and chunking
"""

import os
import threading
from typing import Optional, Dict, Any, List, Generator, Callable
import PyPDF2
import pdfplumber
from dataclasses import dataclass

@dataclass
class DocumentChunk:
    """Represents a chunk of document content"""
    chunk_id: int
    page_start: int
    page_end: int
    content: str
    char_start: int
    char_end: int
    is_loaded: bool = False

@dataclass
class DocumentIndex:
    """Index for quick navigation through large documents"""
    total_pages: int
    total_characters: int
    chunks: List[DocumentChunk]
    page_char_positions: List[int]  # Character position where each page starts

class OptimizedDocumentParser:
    """Enhanced document parser for large files with lazy loading"""
    
    def __init__(self, chunk_size_pages: int = 10, max_chars_per_chunk: int = 50000):
        self.chunk_size_pages = chunk_size_pages
        self.max_chars_per_chunk = max_chars_per_chunk
        self.supported_extensions = {'.pdf', '.txt', '.md'}
        self._cache = {}  # Simple content cache
    
    def is_supported(self, file_path: str) -> bool:
        """Check if file format is supported"""
        _, ext = os.path.splitext(file_path.lower())
        return ext in self.supported_extensions
    
    def parse_document_lazy(self, file_path: str, progress_callback: Optional[Callable[[int, int], None]] = None) -> Dict[str, Any]:
        """Parse document with lazy loading for large files"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_size = os.path.getsize(file_path)
        _, ext = os.path.splitext(file_path.lower())
        
        # For small files, use regular parsing
        if file_size < 5 * 1024 * 1024:  # Less than 5MB
            return self._parse_regular(file_path)
        
        # For large files, use lazy loading
        if ext == '.pdf':
            return self._parse_pdf_lazy(file_path, progress_callback)
        elif ext in {'.txt', '.md'}:
            return self._parse_text_lazy(file_path, progress_callback)
        else:
            raise ValueError(f"Unsupported file format: {ext}")
    
    def _parse_regular(self, file_path: str) -> Dict[str, Any]:
        """Regular parsing for small files"""
        from core.document_parser import DocumentParser
        regular_parser = DocumentParser()
        return regular_parser.parse_document(file_path)
    
    def _parse_pdf_lazy(self, file_path: str, progress_callback: Optional[Callable[[int, int], None]] = None) -> Dict[str, Any]:
        """Parse PDF with lazy loading"""
        try:
            with pdfplumber.open(file_path) as pdf:
                total_pages = len(pdf.pages)
                
                if progress_callback:
                    progress_callback(0, total_pages)
                
                # Create index by reading page boundaries without full content
                chunks = []
                page_char_positions = [0]
                current_char_pos = 0
                
                # Process in chunks
                for chunk_start in range(0, total_pages, self.chunk_size_pages):
                    chunk_end = min(chunk_start + self.chunk_size_pages, total_pages)
                    
                    # Estimate chunk size without loading full content
                    estimated_chars = (chunk_end - chunk_start) * 2000  # Rough estimate
                    
                    chunk = DocumentChunk(
                        chunk_id=len(chunks),
                        page_start=chunk_start,
                        page_end=chunk_end,
                        content="",  # Will be loaded on demand
                        char_start=current_char_pos,
                        char_end=current_char_pos + estimated_chars,
                        is_loaded=False
                    )
                    chunks.append(chunk)
                    current_char_pos += estimated_chars
                    
                    if progress_callback:
                        progress_callback(chunk_end, total_pages)
                
                # Create document index
                doc_index = DocumentIndex(
                    total_pages=total_pages,
                    total_characters=current_char_pos,
                    chunks=chunks,
                    page_char_positions=page_char_positions
                )
                
                return {
                    'content': None,  # Content will be loaded on demand
                    'lazy_content': True,
                    'file_path': file_path,
                    'index': doc_index,
                    'metadata': {
                        'file_path': file_path,
                        'file_type': 'pdf',
                        'total_pages': total_pages,
                        'total_characters': current_char_pos,
                        'is_lazy': True,
                        'chunk_count': len(chunks)
                    }
                }
        
        except Exception as e:
            # Fallback to regular parsing
            return self._parse_regular(file_path)
    
    def _parse_text_lazy(self, file_path: str, progress_callback: Optional[Callable[[int, int], None]] = None) -> Dict[str, Any]:
        """Parse text file with lazy loading"""
        try:
            file_size = os.path.getsize(file_path)
            
            # For text files, create chunks based on character count
            chunks = []
            current_pos = 0
            chunk_id = 0
            
            with open(file_path, 'r', encoding='utf-8') as file:
                while current_pos < file_size:
                    chunk_start = current_pos
                    chunk_end = min(current_pos + self.max_chars_per_chunk, file_size)
                    
                    chunk = DocumentChunk(
                        chunk_id=chunk_id,
                        page_start=0,  # Text files don't have pages
                        page_end=0,
                        content="",  # Will be loaded on demand
                        char_start=chunk_start,
                        char_end=chunk_end,
                        is_loaded=False
                    )
                    chunks.append(chunk)
                    
                    current_pos = chunk_end
                    chunk_id += 1
                    
                    if progress_callback:
                        progress_callback(current_pos, file_size)
            
            doc_index = DocumentIndex(
                total_pages=1,
                total_characters=file_size,
                chunks=chunks,
                page_char_positions=[0]
            )
            
            return {
                'content': None,  # Content will be loaded on demand
                'lazy_content': True,
                'file_path': file_path,
                'index': doc_index,
                'metadata': {
                    'file_path': file_path,
                    'file_type': 'text',
                    'total_characters': file_size,
                    'is_lazy': True,
                    'chunk_count': len(chunks)
                }
            }
        
        except Exception as e:
            return self._parse_regular(file_path)
    
    def load_chunk(self, document_data: Dict[str, Any], chunk_id: int) -> str:
        """Load content for a specific chunk"""
        if not document_data.get('lazy_content', False):
            return document_data.get('content', '')
        
        doc_index = document_data['index']
        if chunk_id >= len(doc_index.chunks):
            return ""
        
        chunk = doc_index.chunks[chunk_id]
        if chunk.is_loaded:
            return chunk.content
        
        # Load chunk content
        file_path = document_data['file_path']
        _, ext = os.path.splitext(file_path.lower())
        
        try:
            if ext == '.pdf':
                chunk.content = self._load_pdf_chunk(file_path, chunk)
            else:
                chunk.content = self._load_text_chunk(file_path, chunk)
            
            chunk.is_loaded = True
            return chunk.content
        
        except Exception as e:
            return f"Error loading chunk {chunk_id}: {str(e)}"
    
    def _load_pdf_chunk(self, file_path: str, chunk: DocumentChunk) -> str:
        """Load content for a PDF chunk"""
        try:
            with pdfplumber.open(file_path) as pdf:
                content_parts = []
                for page_num in range(chunk.page_start, chunk.page_end):
                    if page_num < len(pdf.pages):
                        page_text = pdf.pages[page_num].extract_text() or ""
                        content_parts.append(page_text)
                
                return '\n'.join(content_parts)
        
        except Exception:
            # Fallback to PyPDF2
            try:
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    content_parts = []
                    
                    for page_num in range(chunk.page_start, chunk.page_end):
                        if page_num < len(pdf_reader.pages):
                            page_text = pdf_reader.pages[page_num].extract_text() or ""
                            content_parts.append(page_text)
                    
                    return '\n'.join(content_parts)
            except Exception as e:
                return f"Error loading PDF chunk: {str(e)}"
    
    def _load_text_chunk(self, file_path: str, chunk: DocumentChunk) -> str:
        """Load content for a text chunk"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                file.seek(chunk.char_start)
                content = file.read(chunk.char_end - chunk.char_start)
                return content
        except Exception as e:
            return f"Error loading text chunk: {str(e)}"
    
    def get_text_at_position(self, document_data: Dict[str, Any], start_pos: int, end_pos: int) -> str:
        """Extract text at specific positions, loading chunks as needed"""
        if not document_data.get('lazy_content', False):
            content = document_data.get('content', '')
            return content[start_pos:end_pos]
        
        doc_index = document_data['index']
        result_parts = []
        
        # Find chunks that contain the requested range
        for chunk in doc_index.chunks:
            if chunk.char_end <= start_pos or chunk.char_start >= end_pos:
                continue  # Chunk doesn't overlap with requested range
            
            # Load chunk content
            chunk_content = self.load_chunk(document_data, chunk.chunk_id)
            
            # Calculate positions within the chunk
            chunk_start = max(0, start_pos - chunk.char_start)
            chunk_end = min(len(chunk_content), end_pos - chunk.char_start)
            
            if chunk_start < chunk_end:
                result_parts.append(chunk_content[chunk_start:chunk_end])
        
        return ''.join(result_parts)
    
    def search_in_document(self, document_data: Dict[str, Any], search_term: str, 
                          progress_callback: Optional[Callable[[int, int], None]] = None) -> List[Dict[str, Any]]:
        """Search for term in document, loading chunks as needed"""
        if not document_data.get('lazy_content', False):
            # Regular search for non-lazy documents
            content = document_data.get('content', '')
            results = []
            start = 0
            while True:
                pos = content.find(search_term, start)
                if pos == -1:
                    break
                results.append({
                    'position': pos,
                    'context': content[max(0, pos-50):pos+len(search_term)+50],
                    'chunk_id': None
                })
                start = pos + 1
            return results
        
        # Search in lazy-loaded document
        doc_index = document_data['index']
        results = []
        
        for i, chunk in enumerate(doc_index.chunks):
            if progress_callback:
                progress_callback(i, len(doc_index.chunks))
            
            chunk_content = self.load_chunk(document_data, chunk.chunk_id)
            
            # Search within chunk
            start = 0
            while True:
                pos = chunk_content.find(search_term, start)
                if pos == -1:
                    break
                
                global_pos = chunk.char_start + pos
                context_start = max(0, pos - 50)
                context_end = min(len(chunk_content), pos + len(search_term) + 50)
                
                results.append({
                    'position': global_pos,
                    'context': chunk_content[context_start:context_end],
                    'chunk_id': chunk.chunk_id
                })
                start = pos + 1
        
        return results
    
    def get_chunk_info(self, document_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get information about all chunks in the document"""
        if not document_data.get('lazy_content', False):
            return []
        
        doc_index = document_data['index']
        chunk_info = []
        
        for chunk in doc_index.chunks:
            info = {
                'chunk_id': chunk.chunk_id,
                'page_start': chunk.page_start,
                'page_end': chunk.page_end,
                'char_start': chunk.char_start,
                'char_end': chunk.char_end,
                'is_loaded': chunk.is_loaded,
                'estimated_size': chunk.char_end - chunk.char_start
            }
            chunk_info.append(info)
        
        return chunk_info