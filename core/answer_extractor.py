"""
Optimized answer extraction for large documents with progress tracking
"""

import threading
import time
import re
from typing import List, Dict, Any, Callable, Optional, Generator
from dataclasses import dataclass
from core.document_parser import DocumentParser
from core.llm_client import LLMClient, APIConfig

@dataclass
class AnswerCandidate:
    """Represents a potential answer extracted from text"""
    text: str
    start_pos: int
    end_pos: int
    confidence: float
    extraction_method: str
    context: str = ""

@dataclass
class ExtractionProgress:
    """Progress information for extraction"""
    current_chunk: int
    total_chunks: int
    candidates_found: int
    current_method: str
    is_complete: bool = False
    error_message: Optional[str] = None

class AnswerExtractor:
    """Enhanced answer extractor for large documents with progress tracking"""
    
    def __init__(self):
        self.doc_parser = DocumentParser()
        self.is_extracting = False
        self.stop_extraction = False
        
        # Base extraction settings
        self.min_answer_length = 20
        self.max_answer_length = 500
        self.min_confidence = 0.3
        
        # Extraction settings for large documents
        self.max_candidates_per_chunk = 100
        self.overlap_size = 200  # Characters to overlap between chunks to catch split sentences
    
    def extract_answers_optimized(self, 
                                document_data: Dict[str, Any], 
                                methods: List[str] = None,
                                progress_callback: Optional[Callable[[ExtractionProgress], None]] = None,
                                max_candidates: int = 5000,
                                chunk_range: Optional[Dict[str, int]] = None,
                                ai_config: Optional[APIConfig] = None,
                                ai_max_pairs: int = 25,
                                ai_custom_prompt: Optional[str] = None) -> List[AnswerCandidate]:
        """Extract answers with optimization for large documents"""
        
        if methods is None:
            methods = ['sentences', 'paragraphs', 'lists', 'definitions', 'facts']
        
        # Handle AI extraction separately
        if 'ai' in methods:
            if ai_config is None:
                raise ValueError("AI extraction requires ai_config parameter")
            return self.extract_answers_ai(document_data, progress_callback, max_candidates, chunk_range, 
                                         ai_config, ai_max_pairs, ai_custom_prompt)
        
        all_candidates = []
        
        # Check if document uses lazy loading
        if document_data.get('lazy_content', False):
            all_candidates = self._extract_from_lazy_document(
                document_data, methods, progress_callback, max_candidates
            )
        else:
            # Regular extraction for small documents
            content = document_data.get('content', '')
            all_candidates = self.extract_answers(content, methods)
            
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
        all_candidates = self._deduplicate_candidates(all_candidates)
        all_candidates = self._filter_candidates(all_candidates)
        
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
        candidates = self.extract_answers(content, methods)
        
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
                                max_candidates: int = 5000,
                                chunk_range: Optional[Dict[str, int]] = None,
                                ai_config: Optional[APIConfig] = None,
                                ai_max_pairs: int = 25,
                                ai_custom_prompt: Optional[str] = None):
        """Extract answers in a separate thread"""
        
        def extraction_worker():
            try:
                self.is_extracting = True
                self.stop_extraction = False
                
                # Ensure AI parameters have defaults when not provided
                final_ai_max_pairs = ai_max_pairs if ai_config is not None else 25
                final_ai_custom_prompt = ai_custom_prompt if ai_config is not None else None
                
                candidates = self.extract_answers_optimized(
                    document_data, methods, progress_callback, max_candidates, chunk_range, 
                    ai_config, final_ai_max_pairs, final_ai_custom_prompt
                )
                
                if completion_callback:
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
            candidates = self.extract_answers(content, methods)
            
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
            'min_answer_length': self.min_answer_length,
            'max_answer_length': self.max_answer_length,
            'min_confidence': self.min_confidence
        }
    
    def update_extraction_settings(self, **kwargs):
        """Update extraction settings"""
        if 'max_candidates_per_chunk' in kwargs:
            self.max_candidates_per_chunk = kwargs['max_candidates_per_chunk']
        if 'overlap_size' in kwargs:
            self.overlap_size = kwargs['overlap_size']
        
        # Update extraction settings
        self.set_filters(
            kwargs.get('min_length'),
            kwargs.get('max_length'),
            kwargs.get('min_confidence')
        )
    
    def extract_answers(self, text: str, methods: List[str] = None) -> List[AnswerCandidate]:
        """Extract answer candidates using specified methods"""
        if methods is None:
            methods = ['sentences', 'paragraphs', 'lists', 'definitions', 'facts']
        
        candidates = []
        
        for method in methods:
            if method == 'sentences':
                candidates.extend(self._extract_sentences(text))
            elif method == 'paragraphs':
                candidates.extend(self._extract_paragraphs(text))
            elif method == 'lists':
                candidates.extend(self._extract_list_items(text))
            elif method == 'definitions':
                candidates.extend(self._extract_definitions(text))
            elif method == 'facts':
                candidates.extend(self._extract_facts(text))
            elif method == 'procedures':
                candidates.extend(self._extract_procedures(text))
        
        # Remove duplicates and apply filters
        candidates = self._deduplicate_candidates(candidates)
        candidates = self._filter_candidates(candidates)
        
        # Sort by confidence score
        candidates.sort(key=lambda x: x.confidence, reverse=True)
        
        return candidates
    
    def _extract_sentences(self, text: str) -> List[AnswerCandidate]:
        """Extract individual sentences as answer candidates"""
        candidates = []
        
        # Split into sentences using multiple delimiters
        sentence_pattern = r'[.!?]+\s+'
        sentences = re.split(sentence_pattern, text)
        
        current_pos = 0
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # Find actual position in text
            start_pos = text.find(sentence, current_pos)
            if start_pos == -1:
                current_pos += len(sentence) + 1
                continue
                
            end_pos = start_pos + len(sentence)
            
            # Calculate confidence based on sentence characteristics
            confidence = self._score_sentence(sentence)
            
            if confidence > 0:
                candidates.append(AnswerCandidate(
                    text=sentence,
                    start_pos=start_pos,
                    end_pos=end_pos,
                    confidence=confidence,
                    extraction_method='sentences'
                ))
            
            current_pos = end_pos + 1
        
        return candidates
    
    def _extract_paragraphs(self, text: str) -> List[AnswerCandidate]:
        """Extract paragraphs as answer candidates"""
        candidates = []
        
        # Split by double newlines or similar paragraph separators
        paragraphs = re.split(r'\n\s*\n', text)
        
        current_pos = 0
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            # Find actual position in text
            start_pos = text.find(paragraph, current_pos)
            if start_pos == -1:
                current_pos += len(paragraph) + 2
                continue
                
            end_pos = start_pos + len(paragraph)
            
            # Score paragraph
            confidence = self._score_paragraph(paragraph)
            
            if confidence > 0 and self.min_answer_length <= len(paragraph) <= self.max_answer_length:
                candidates.append(AnswerCandidate(
                    text=paragraph,
                    start_pos=start_pos,
                    end_pos=end_pos,
                    confidence=confidence,
                    extraction_method='paragraphs'
                ))
            
            current_pos = end_pos + 2
        
        return candidates
    
    def _extract_list_items(self, text: str) -> List[AnswerCandidate]:
        """Extract list items and numbered points"""
        candidates = []
        
        # Patterns for different list types
        patterns = [
            r'^\s*[\-\*\+]\s+(.+)$',  # Bullet points
            r'^\s*\d+\.\s+(.+)$',     # Numbered lists
            r'^\s*[a-zA-Z]\.\s+(.+)$', # Lettered lists
            r'^\s*•\s+(.+)$',         # Unicode bullets
        ]
        
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            for pattern in patterns:
                match = re.match(pattern, line, re.MULTILINE)
                if match:
                    list_item = match.group(1).strip()
                    
                    if self.min_answer_length <= len(list_item) <= self.max_answer_length:
                        # Find position in original text
                        start_pos = text.find(list_item)
                        if start_pos != -1:
                            end_pos = start_pos + len(list_item)
                            
                            confidence = self._score_list_item(list_item)
                            
                            candidates.append(AnswerCandidate(
                                text=list_item,
                                start_pos=start_pos,
                                end_pos=end_pos,
                                confidence=confidence,
                                extraction_method='lists'
                            ))
        
        return candidates
    
    def _extract_definitions(self, text: str) -> List[AnswerCandidate]:
        """Extract definitions and explanatory statements"""
        candidates = []
        
        # Patterns for definitions
        definition_patterns = [
            r'(.+?)\s+is\s+(.+?)[.!?]',           # "X is Y"
            r'(.+?)\s+are\s+(.+?)[.!?]',          # "X are Y"
            r'(.+?)\s+means\s+(.+?)[.!?]',        # "X means Y"
            r'(.+?)\s+refers to\s+(.+?)[.!?]',    # "X refers to Y"
            r'(.+?):\s+(.+?)[.!?]',               # "X: Y"
            r'(.+?)\s+can be defined as\s+(.+?)[.!?]', # "X can be defined as Y"
        ]
        
        for pattern in definition_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                definition = match.group(0).strip()
                
                if self.min_answer_length <= len(definition) <= self.max_answer_length:
                    confidence = self._score_definition(definition)
                    
                    candidates.append(AnswerCandidate(
                        text=definition,
                        start_pos=match.start(),
                        end_pos=match.end(),
                        confidence=confidence,
                        extraction_method='definitions'
                    ))
        
        return candidates
    
    def _extract_facts(self, text: str) -> List[AnswerCandidate]:
        """Extract factual statements"""
        candidates = []
        
        # Patterns for factual statements
        fact_patterns = [
            r'According to\s+.+?,\s+(.+?)[.!?]',   # "According to X, Y"
            r'Research shows\s+(.+?)[.!?]',        # "Research shows X"
            r'Studies indicate\s+(.+?)[.!?]',      # "Studies indicate X"
            r'It is known that\s+(.+?)[.!?]',      # "It is known that X"
            r'The fact is\s+(.+?)[.!?]',           # "The fact is X"
            r'\d+%\s+of\s+(.+?)[.!?]',             # "X% of Y"
            r'In\s+\d{4},\s+(.+?)[.!?]',           # "In YYYY, X"
        ]
        
        for pattern in fact_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                fact = match.group(0).strip()
                
                if self.min_answer_length <= len(fact) <= self.max_answer_length:
                    confidence = self._score_fact(fact)
                    
                    candidates.append(AnswerCandidate(
                        text=fact,
                        start_pos=match.start(),
                        end_pos=match.end(),
                        confidence=confidence,
                        extraction_method='facts'
                    ))
        
        return candidates
    
    def _extract_procedures(self, text: str) -> List[AnswerCandidate]:
        """Extract procedural or how-to information"""
        candidates = []
        
        # Look for step-by-step procedures
        procedure_patterns = [
            r'First,\s+(.+?)[.!?]',                # "First, X"
            r'Then,\s+(.+?)[.!?]',                 # "Then, X"
            r'Next,\s+(.+?)[.!?]',                 # "Next, X"
            r'Finally,\s+(.+?)[.!?]',              # "Finally, X"
            r'To\s+.+?,\s+(.+?)[.!?]',            # "To do X, Y"
            r'In order to\s+.+?,\s+(.+?)[.!?]',   # "In order to X, Y"
        ]
        
        for pattern in procedure_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                procedure = match.group(0).strip()
                
                if self.min_answer_length <= len(procedure) <= self.max_answer_length:
                    confidence = self._score_procedure(procedure)
                    
                    candidates.append(AnswerCandidate(
                        text=procedure,
                        start_pos=match.start(),
                        end_pos=match.end(),
                        confidence=confidence,
                        extraction_method='procedures'
                    ))
        
        return candidates
    
    def _score_sentence(self, sentence: str) -> float:
        """Score a sentence for its potential as an answer"""
        score = 0.5  # Base score
        
        # Length scoring
        if 50 <= len(sentence) <= 200:
            score += 0.2
        elif len(sentence) < self.min_answer_length:
            return 0.0
        
        # Content scoring
        if re.search(r'\b(is|are|was|were|will|can|could|should|must)\b', sentence, re.IGNORECASE):
            score += 0.1
        
        if re.search(r'\b(because|since|due to|as a result)\b', sentence, re.IGNORECASE):
            score += 0.1
        
        if re.search(r'\b(therefore|thus|consequently|however)\b', sentence, re.IGNORECASE):
            score += 0.1
        
        # Avoid questions and incomplete sentences
        if sentence.strip().endswith('?'):
            score -= 0.3
        
        if sentence.count(',') > 3:  # Complex sentences
            score += 0.1
        
        return min(score, 1.0)
    
    def _score_paragraph(self, paragraph: str) -> float:
        """Score a paragraph for its potential as an answer"""
        score = 0.4  # Base score
        
        # Length scoring
        if 100 <= len(paragraph) <= 400:
            score += 0.3
        elif len(paragraph) > self.max_answer_length:
            return 0.0
        
        # Sentence count
        sentence_count = len(re.split(r'[.!?]+', paragraph))
        if 2 <= sentence_count <= 5:
            score += 0.2
        
        # Content coherence
        if paragraph.count('\n') == 0:  # Single paragraph
            score += 0.1
        
        return min(score, 1.0)
    
    def _score_list_item(self, item: str) -> float:
        """Score a list item for its potential as an answer"""
        score = 0.6  # List items are often good answers
        
        if 30 <= len(item) <= 150:
            score += 0.2
        
        # Avoid incomplete items
        if item.endswith(('...', ':')):
            score -= 0.3
        
        return min(score, 1.0)
    
    def _score_definition(self, definition: str) -> float:
        """Score a definition for its potential as an answer"""
        score = 0.8  # Definitions are usually excellent answers
        
        if 40 <= len(definition) <= 200:
            score += 0.1
        
        return min(score, 1.0)
    
    def _score_fact(self, fact: str) -> float:
        """Score a factual statement for its potential as an answer"""
        score = 0.7  # Facts are usually good answers
        
        if 30 <= len(fact) <= 150:
            score += 0.1
        
        # Statistical information
        if re.search(r'\d+%|\d+\s+(percent|million|billion|thousand)', fact):
            score += 0.1
        
        return min(score, 1.0)
    
    def _score_procedure(self, procedure: str) -> float:
        """Score a procedural statement for its potential as an answer"""
        score = 0.6  # Procedures are good for how-to questions
        
        if 40 <= len(procedure) <= 200:
            score += 0.2
        
        return min(score, 1.0)
    
    def _deduplicate_candidates(self, candidates: List[AnswerCandidate]) -> List[AnswerCandidate]:
        """Remove duplicate or overlapping candidates"""
        if not candidates:
            return candidates
        
        # Sort by position
        candidates.sort(key=lambda x: x.start_pos)
        
        deduplicated = []
        for candidate in candidates:
            # Check for overlaps with existing candidates
            overlap_found = False
            for existing in deduplicated:
                # Check if there's significant overlap
                overlap_start = max(candidate.start_pos, existing.start_pos)
                overlap_end = min(candidate.end_pos, existing.end_pos)
                overlap_length = max(0, overlap_end - overlap_start)
                
                min_length = min(len(candidate.text), len(existing.text))
                overlap_ratio = overlap_length / min_length if min_length > 0 else 0
                
                if overlap_ratio > 0.7:  # 70% overlap threshold
                    overlap_found = True
                    # Keep the one with higher confidence
                    if candidate.confidence > existing.confidence:
                        deduplicated.remove(existing)
                        deduplicated.append(candidate)
                    break
            
            if not overlap_found:
                deduplicated.append(candidate)
        
        return deduplicated
    
    def _filter_candidates(self, candidates: List[AnswerCandidate]) -> List[AnswerCandidate]:
        """Filter candidates based on quality criteria"""
        filtered = []
        
        for candidate in candidates:
            # Apply filters
            if candidate.confidence < self.min_confidence:
                continue
            
            if len(candidate.text) < self.min_answer_length:
                continue
                
            if len(candidate.text) > self.max_answer_length:
                continue
            
            # Filter out candidates that are mostly punctuation or whitespace
            clean_text = re.sub(r'[^\w\s]', '', candidate.text)
            if len(clean_text.strip()) < self.min_answer_length * 0.7:
                continue
            
            # Filter out candidates with too many consecutive capitals (likely headers)
            if re.search(r'[A-Z]{5,}', candidate.text):
                continue
            
            filtered.append(candidate)
        
        return filtered
    
    def set_filters(self, min_length: int = None, max_length: int = None, min_confidence: float = None):
        """Update extraction filters"""
        if min_length is not None:
            self.min_answer_length = min_length
        if max_length is not None:
            self.max_answer_length = max_length
        if min_confidence is not None:
            self.min_confidence = min_confidence
    
    def extract_answers_ai(self,
                          document_data: Dict[str, Any],
                          progress_callback: Optional[Callable[[ExtractionProgress], None]] = None,
                          max_candidates: int = 5000,
                          chunk_range: Optional[Dict[str, int]] = None,
                          ai_config: Optional[APIConfig] = None,
                          ai_max_pairs: int = 25,
                          ai_custom_prompt: Optional[str] = None) -> List[AnswerCandidate]:
        """Extract Q&A pairs using AI and return as answer candidates"""
        
        # Use provided AI configuration or load from file
        try:
            if ai_config:
                llm_client = LLMClient(ai_config)
            else:
                import json
                import os
                config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'api_config.json')
                with open(config_path, 'r') as f:
                    api_config_data = json.load(f)
                
                config = APIConfig(
                    provider=api_config_data['provider'],
                    api_key=api_config_data['api_key'],
                    base_url=LLMClient.get_base_url(api_config_data['provider']),
                    model=api_config_data['model']
                )
                
                llm_client = LLMClient(config)
            
        except Exception as e:
            if progress_callback:
                progress = ExtractionProgress(
                    current_chunk=0,
                    total_chunks=0,
                    candidates_found=0,
                    current_method='ai',
                    is_complete=True,
                    error_message=f"Failed to load API configuration: {str(e)}"
                )
                progress_callback(progress)
            return []
        
        all_candidates = []
        
        # Check if document uses lazy loading
        if document_data.get('lazy_content', False):
            all_candidates = self._extract_ai_from_lazy_document(
                document_data, llm_client, progress_callback, max_candidates, chunk_range,
                ai_max_pairs, ai_custom_prompt
            )
        else:
            # Process entire document at once for small documents
            content = document_data.get('content', '')
            if content:
                try:
                    if progress_callback:
                        progress = ExtractionProgress(
                            current_chunk=1,
                            total_chunks=1,
                            candidates_found=0,
                            current_method='ai'
                        )
                        progress_callback(progress)
                    
                    qa_pairs = llm_client.extract_qa_pairs_from_text(content, max_pairs=ai_max_pairs, custom_prompt=ai_custom_prompt)
                    all_candidates = self._convert_qa_pairs_to_candidates(qa_pairs, content)
                    
                    if progress_callback:
                        progress = ExtractionProgress(
                            current_chunk=1,
                            total_chunks=1,
                            candidates_found=len(all_candidates),
                            current_method='ai',
                            is_complete=True
                        )
                        progress_callback(progress)
                        
                except Exception as e:
                    if progress_callback:
                        progress = ExtractionProgress(
                            current_chunk=1,
                            total_chunks=1,
                            candidates_found=0,
                            current_method='ai',
                            is_complete=True,
                            error_message=str(e)
                        )
                        progress_callback(progress)
        
        return all_candidates[:max_candidates]
    
    def _extract_ai_from_lazy_document(self,
                                     document_data: Dict[str, Any],
                                     llm_client: LLMClient,
                                     progress_callback: Optional[Callable[[ExtractionProgress], None]],
                                     max_candidates: int,
                                     chunk_range: Optional[Dict[str, int]] = None,
                                     ai_max_pairs: int = 25,
                                     ai_custom_prompt: Optional[str] = None) -> List[AnswerCandidate]:
        """Extract Q&A pairs from lazy-loaded document using AI"""
        
        doc_index = document_data['index']
        all_candidates = []
        total_chunks = len(doc_index.chunks)
        
        # Determine chunk range to process
        start_chunk = 0
        end_chunk = total_chunks
        
        if chunk_range:
            start_chunk = chunk_range.get('start', 0)
            end_chunk = chunk_range.get('end', total_chunks)
            # Ensure valid range
            start_chunk = max(0, min(start_chunk, total_chunks))
            end_chunk = max(start_chunk, min(end_chunk, total_chunks))
        
        # Process only the specified chunk range
        chunks_to_process = doc_index.chunks[start_chunk:end_chunk]
        
        for chunk_idx, chunk in enumerate(chunks_to_process, start=start_chunk):
            if self.stop_extraction:
                break
                
            if len(all_candidates) >= max_candidates:
                break
            
            # Load chunk content
            chunk_content = self.doc_parser.load_chunk(document_data, chunk.chunk_id)
            
            if not chunk_content.strip():
                continue
            
            try:
                if progress_callback:
                    # Report progress relative to the chunk range being processed
                    current_progress = chunk_idx - start_chunk + 1
                    total_progress = end_chunk - start_chunk
                    progress = ExtractionProgress(
                        current_chunk=current_progress,
                        total_chunks=total_progress,
                        candidates_found=len(all_candidates),
                        current_method='ai'
                    )
                    progress_callback(progress)
                
                # Extract Q&A pairs from this chunk
                qa_pairs = llm_client.extract_qa_pairs_from_text(chunk_content, max_pairs=ai_max_pairs, custom_prompt=ai_custom_prompt)
                
                # Convert Q&A pairs to candidates
                chunk_candidates = self._convert_qa_pairs_to_candidates(qa_pairs, chunk_content, chunk.char_start)
                all_candidates.extend(chunk_candidates)
                
            except Exception as e:
                print(f"Error processing chunk {chunk_idx}: {e}")
                # If it's an API error, add more context
                if "404" in str(e) or "API request failed" in str(e):
                    print(f"API configuration issue detected. Check your API settings.")
                    # For now, continue with next chunk, but could also abort here
                continue
        
        if progress_callback:
            # Report completion relative to the chunk range processed
            total_progress = end_chunk - start_chunk
            progress = ExtractionProgress(
                current_chunk=total_progress,
                total_chunks=total_progress,
                candidates_found=len(all_candidates),
                current_method='ai',
                is_complete=True
            )
            progress_callback(progress)
        
        return all_candidates
    
    def _convert_qa_pairs_to_candidates(self, 
                                      qa_pairs: List[Dict[str, str]], 
                                      source_text: str,
                                      char_offset: int = 0) -> List[AnswerCandidate]:
        """Convert Q&A pairs to AnswerCandidate objects"""
        candidates = []
        
        for qa_pair in qa_pairs:
            answer_text = qa_pair.get('answer', '').strip()
            question_text = qa_pair.get('question', '').strip()
            
            if not answer_text or not question_text:
                continue
            
            # Find the answer position in source text
            start_pos = source_text.find(answer_text)
            if start_pos == -1:
                # Try fuzzy matching for slight variations
                start_pos = self._fuzzy_find_answer(answer_text, source_text)
            
            if start_pos != -1:
                end_pos = start_pos + len(answer_text)
                
                candidate = AnswerCandidate(
                    text=answer_text,
                    start_pos=start_pos + char_offset,
                    end_pos=end_pos + char_offset,
                    confidence=0.9,  # High confidence for AI-extracted answers
                    extraction_method='ai',
                    context=question_text  # Store the question in context
                )
                candidates.append(candidate)
        
        return candidates
    
    def _fuzzy_find_answer(self, answer_text: str, source_text: str) -> int:
        """Attempt fuzzy matching to find answer in source text"""
        # Try to find the answer with some tolerance for punctuation/whitespace differences
        import re
        
        # Normalize whitespace and punctuation
        normalized_answer = re.sub(r'\s+', ' ', answer_text.strip())
        normalized_source = re.sub(r'\s+', ' ', source_text)
        
        # Try exact match first
        pos = normalized_source.find(normalized_answer)
        if pos != -1:
            return pos
        
        # Try removing some punctuation
        clean_answer = re.sub(r'[^\w\s]', '', normalized_answer)
        clean_source = re.sub(r'[^\w\s]', '', normalized_source)
        
        pos = clean_source.find(clean_answer)
        if pos != -1:
            # Map back to original position (approximately)
            return source_text.find(answer_text[:20])  # Use first 20 chars as anchor
        
        return -1
    
    def get_ai_qa_pairs(self, document_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract Q&A pairs using AI and return them directly (for UI integration)"""
        
        # This method is used by the UI to get Q&A pairs ready for the question generator
        candidates = self.extract_answers_ai(document_data, progress_callback=None, max_candidates=5000, 
                                           chunk_range=None, ai_config=None, ai_max_pairs=25, ai_custom_prompt=None)
        
        qa_pairs = []
        for candidate in candidates:
            if candidate.context:  # Context contains the question
                qa_pairs.append({
                    'question': candidate.context,
                    'answer': candidate.text
                })
        
        return qa_pairs