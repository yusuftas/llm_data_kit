"""
Optimized answer extraction for large documents with progress tracking
"""

import threading
import time
from typing import List, Dict, Any, Callable, Optional, Generator
from dataclasses import dataclass
from core.answer_extractor import AnswerExtractor, AnswerCandidate
from core.document_parser import DocumentParser

@dataclass
class ExtractionProgress:
    """Progress information for extraction"""
    current_chunk: int
    total_chunks: int
    candidates_found: int
    current_method: str
    is_complete: bool = False
    error_message: Optional[str] = None

class OptimizedAnswerExtractor:
    """Enhanced answer extractor for large documents with progress tracking"""
    
    def __init__(self, base_extractor: Optional[AnswerExtractor] = None):
        self.base_extractor = base_extractor or AnswerExtractor()
        self.doc_parser = DocumentParser()
        self.is_extracting = False
        self.stop_extraction = False
        
        # Extraction settings for large documents
        self.max_candidates_per_chunk = 100
        self.overlap_size = 200  # Characters to overlap between chunks to catch split sentences
    
    def extract_answers_optimized(self, 
                                document_data: Dict[str, Any], 
                                methods: List[str] = None,
                                progress_callback: Optional[Callable[[ExtractionProgress], None]] = None,
                                max_candidates: int = 5000) -> List[AnswerCandidate]:
        """Extract answers with optimization for large documents"""
        
        if methods is None:
            methods = ['sentences', 'paragraphs', 'lists', 'definitions', 'facts']
        
        all_candidates = []
        
        # Check if document uses lazy loading
        if document_data.get('lazy_content', False):
            all_candidates = self._extract_from_lazy_document(
                document_data, methods, progress_callback, max_candidates
            )
        else:
            # Regular extraction for small documents
            content = document_data.get('content', '')
            all_candidates = self.base_extractor.extract_answers(content, methods)
            
            if progress_callback:
                progress = ExtractionProgress(
                    current_chunk=1,
                    total_chunks=1,
                    candidates_found=len(all_candidates),
                    current_method='complete',
                    is_complete=True
                )
                progress_callback(progress)
        
        return all_candidates[:max_candidates]  # Limit results
    
    def _extract_from_lazy_document(self,
                                  document_data: Dict[str, Any],
                                  methods: List[str],
                                  progress_callback: Optional[Callable[[ExtractionProgress], None]],
                                  max_candidates: int) -> List[AnswerCandidate]:
        """Extract answers from lazy-loaded document"""
        
        doc_index = document_data['index']
        all_candidates = []
        
        total_chunks = len(doc_index.chunks)
        
        for chunk_idx, chunk in enumerate(doc_index.chunks):
            if self.stop_extraction:
                break
                
            if len(all_candidates) >= max_candidates:
                break
            
            # Load chunk content
            chunk_content = self.doc_parser.load_chunk(document_data, chunk.chunk_id)
            
            # Add overlap from previous chunk to catch split sentences
            if chunk_idx > 0 and len(all_candidates) > 0:
                # Get some content from the end of previous chunk
                prev_chunk = doc_index.chunks[chunk_idx - 1]
                if prev_chunk.is_loaded:
                    prev_content = prev_chunk.content[-self.overlap_size:]
                    chunk_content = prev_content + chunk_content
            
            # Extract from this chunk
            for method in methods:
                if self.stop_extraction or len(all_candidates) >= max_candidates:
                    break
                
                if progress_callback:
                    progress = ExtractionProgress(
                        current_chunk=chunk_idx + 1,
                        total_chunks=total_chunks,
                        candidates_found=len(all_candidates),
                        current_method=method
                    )
                    progress_callback(progress)
                
                chunk_candidates = self._extract_from_chunk(
                    chunk_content, [method], chunk.char_start
                )
                
                # Limit candidates per chunk to prevent memory issues
                chunk_candidates = chunk_candidates[:self.max_candidates_per_chunk]
                all_candidates.extend(chunk_candidates)
        
        # Final deduplication and filtering
        all_candidates = self.base_extractor._deduplicate_candidates(all_candidates)
        all_candidates = self.base_extractor._filter_candidates(all_candidates)
        
        if progress_callback:
            progress = ExtractionProgress(
                current_chunk=total_chunks,
                total_chunks=total_chunks,
                candidates_found=len(all_candidates),
                current_method='complete',
                is_complete=True
            )
            progress_callback(progress)
        
        return all_candidates
    
    def _extract_from_chunk(self, content: str, methods: List[str], char_offset: int = 0) -> List[AnswerCandidate]:
        """Extract candidates from a single chunk"""
        candidates = self.base_extractor.extract_answers(content, methods)
        
        # Adjust positions to account for chunk offset
        for candidate in candidates:
            candidate.start_pos += char_offset
            candidate.end_pos += char_offset
        
        return candidates
    
    def extract_answers_threaded(self,
                                document_data: Dict[str, Any],
                                methods: List[str] = None,
                                progress_callback: Optional[Callable[[ExtractionProgress], None]] = None,
                                completion_callback: Optional[Callable[[List[AnswerCandidate]], None]] = None,
                                error_callback: Optional[Callable[[str], None]] = None,
                                max_candidates: int = 5000):
        """Extract answers in a separate thread"""
        
        def extraction_worker():
            try:
                self.is_extracting = True
                self.stop_extraction = False
                
                candidates = self.extract_answers_optimized(
                    document_data, methods, progress_callback, max_candidates
                )
                
                if completion_callback and not self.stop_extraction:
                    completion_callback(candidates)
                    
            except Exception as e:
                if error_callback:
                    error_callback(str(e))
                elif progress_callback:
                    progress = ExtractionProgress(
                        current_chunk=0,
                        total_chunks=0,
                        candidates_found=0,
                        current_method='error',
                        is_complete=True,
                        error_message=str(e)
                    )
                    progress_callback(progress)
            finally:
                self.is_extracting = False
        
        thread = threading.Thread(target=extraction_worker, daemon=True)
        thread.start()
        return thread
    
    def stop_current_extraction(self):
        """Stop the current extraction process"""
        self.stop_extraction = True
    
    def extract_answers_generator(self,
                                document_data: Dict[str, Any],
                                methods: List[str] = None,
                                chunk_size: int = 50) -> Generator[List[AnswerCandidate], None, None]:
        """Generator that yields candidates in batches for progressive loading"""
        
        if methods is None:
            methods = ['sentences', 'paragraphs', 'lists', 'definitions', 'facts']
        
        if not document_data.get('lazy_content', False):
            # For small documents, extract all at once
            content = document_data.get('content', '')
            candidates = self.base_extractor.extract_answers(content, methods)
            
            # Yield in chunks
            for i in range(0, len(candidates), chunk_size):
                yield candidates[i:i + chunk_size]
            return
        
        # For large documents, process chunk by chunk
        doc_index = document_data['index']
        current_batch = []
        
        for chunk in doc_index.chunks:
            if self.stop_extraction:
                break
            
            chunk_content = self.doc_parser.load_chunk(document_data, chunk.chunk_id)
            chunk_candidates = self._extract_from_chunk(
                chunk_content, methods, chunk.char_start
            )
            
            current_batch.extend(chunk_candidates)
            
            # Yield when we have enough candidates
            while len(current_batch) >= chunk_size:
                yield current_batch[:chunk_size]
                current_batch = current_batch[chunk_size:]
        
        # Yield remaining candidates
        if current_batch:
            yield current_batch
    
    def estimate_extraction_time(self, document_data: Dict[str, Any], methods: List[str] = None) -> Dict[str, Any]:
        """Estimate extraction time and resource usage"""
        
        if methods is None:
            methods = ['sentences', 'paragraphs', 'lists', 'definitions', 'facts']
        
        metadata = document_data.get('metadata', {})
        total_chars = metadata.get('total_characters', 0)
        
        # Rough estimates based on method complexity
        method_complexity = {
            'sentences': 1.0,
            'paragraphs': 0.8,
            'lists': 1.2,
            'definitions': 1.5,
            'facts': 2.0,
            'procedures': 1.8
        }
        
        complexity_factor = sum(method_complexity.get(method, 1.0) for method in methods)
        
        # Estimate processing time (very rough)
        chars_per_second = 50000  # Rough estimate
        estimated_seconds = (total_chars * complexity_factor) / chars_per_second
        
        # Estimate memory usage
        if document_data.get('lazy_content', False):
            # Lazy loading uses much less memory
            estimated_memory_mb = min(100, total_chars / 10000)  # Cap at 100MB
        else:
            # Regular loading keeps everything in memory
            estimated_memory_mb = total_chars / 1000  # Very rough estimate
        
        # Estimate candidate count
        estimated_candidates = min(
            total_chars // 100,  # Rough ratio
            5000  # Cap at 5000
        )
        
        return {
            'estimated_time_seconds': estimated_seconds,
            'estimated_memory_mb': estimated_memory_mb,
            'estimated_candidates': estimated_candidates,
            'complexity_factor': complexity_factor,
            'total_characters': total_chars,
            'uses_lazy_loading': document_data.get('lazy_content', False),
            'chunk_count': len(document_data.get('index', {}).get('chunks', []))
        }
    
    def get_extraction_settings(self) -> Dict[str, Any]:
        """Get current extraction settings"""
        return {
            'max_candidates_per_chunk': self.max_candidates_per_chunk,
            'overlap_size': self.overlap_size,
            'min_answer_length': self.base_extractor.min_answer_length,
            'max_answer_length': self.base_extractor.max_answer_length,
            'min_confidence': self.base_extractor.min_confidence
        }
    
    def update_extraction_settings(self, **kwargs):
        """Update extraction settings"""
        if 'max_candidates_per_chunk' in kwargs:
            self.max_candidates_per_chunk = kwargs['max_candidates_per_chunk']
        if 'overlap_size' in kwargs:
            self.overlap_size = kwargs['overlap_size']
        
        # Update base extractor settings
        self.base_extractor.set_filters(
            kwargs.get('min_length'),
            kwargs.get('max_length'),
            kwargs.get('min_confidence')
        )