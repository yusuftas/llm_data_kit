"""
Document parsing utilities for PDF and text files
"""

import os
from typing import Optional, Dict, Any
import PyPDF2
import pdfplumber

class DocumentParser:
    """Handles parsing of various document formats"""
    
    def __init__(self):
        self.supported_extensions = {'.pdf', '.txt', '.md'}
    
    def is_supported(self, file_path: str) -> bool:
        """Check if file format is supported"""
        _, ext = os.path.splitext(file_path.lower())
        return ext in self.supported_extensions
    
    def parse_document(self, file_path: str) -> Dict[str, Any]:
        """Parse document and return content with metadata"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        _, ext = os.path.splitext(file_path.lower())
        
        if ext == '.pdf':
            return self._parse_pdf(file_path)
        elif ext in {'.txt', '.md'}:
            return self._parse_text(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")
    
    def _parse_pdf(self, file_path: str) -> Dict[str, Any]:
        """Parse PDF file using pdfplumber for better text extraction"""
        try:
            with pdfplumber.open(file_path) as pdf:
                text_content = []
                page_info = []
                
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text() or ""
                    text_content.append(page_text)
                    page_info.append({
                        'page_number': page_num,
                        'char_start': sum(len(p) + 1 for p in text_content[:-1]),  # +1 for newlines
                        'char_end': sum(len(p) + 1 for p in text_content[:-1]) + len(page_text),
                        'text_length': len(page_text)
                    })
                
                full_text = '\n'.join(text_content)
                
                return {
                    'content': full_text,
                    'metadata': {
                        'file_path': file_path,
                        'file_type': 'pdf',
                        'total_pages': len(pdf.pages),
                        'total_characters': len(full_text),
                        'page_info': page_info
                    }
                }
        
        except Exception as e:
            # Fallback to PyPDF2 if pdfplumber fails
            return self._parse_pdf_fallback(file_path)
    
    def _parse_pdf_fallback(self, file_path: str) -> Dict[str, Any]:
        """Fallback PDF parsing using PyPDF2"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text_content = []
                
                for page_num, page in enumerate(pdf_reader.pages, 1):
                    page_text = page.extract_text() or ""
                    text_content.append(page_text)
                
                full_text = '\n'.join(text_content)
                
                return {
                    'content': full_text,
                    'metadata': {
                        'file_path': file_path,
                        'file_type': 'pdf',
                        'total_pages': len(pdf_reader.pages),
                        'total_characters': len(full_text),
                        'extraction_method': 'PyPDF2_fallback'
                    }
                }
        
        except Exception as e:
            raise Exception(f"Failed to parse PDF: {str(e)}")
    
    def _parse_text(self, file_path: str) -> Dict[str, Any]:
        """Parse plain text files"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            return {
                'content': content,
                'metadata': {
                    'file_path': file_path,
                    'file_type': 'text',
                    'total_characters': len(content),
                    'total_lines': content.count('\n') + 1
                }
            }
        
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(file_path, 'r', encoding='latin-1') as file:
                    content = file.read()
                
                return {
                    'content': content,
                    'metadata': {
                        'file_path': file_path,
                        'file_type': 'text',
                        'total_characters': len(content),
                        'total_lines': content.count('\n') + 1,
                        'encoding': 'latin-1'
                    }
                }
            except Exception as e:
                raise Exception(f"Failed to parse text file: {str(e)}")
        
        except Exception as e:
            raise Exception(f"Failed to parse text file: {str(e)}")
    
    def get_text_at_position(self, document_data: Dict[str, Any], start_pos: int, end_pos: int) -> str:
        """Extract text from document at specific character positions"""
        content = document_data.get('content', '')
        return content[start_pos:end_pos]