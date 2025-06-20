"""
Automatic answer extraction from documents
"""

import re
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass

@dataclass
class AnswerCandidate:
    """Represents a potential answer extracted from text"""
    text: str
    start_pos: int
    end_pos: int
    confidence: float
    extraction_method: str
    context: str = ""

class AnswerExtractor:
    """Extracts potential answers from document text using various strategies"""
    
    def __init__(self):
        self.min_answer_length = 20
        self.max_answer_length = 500
        self.min_confidence = 0.3
        
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