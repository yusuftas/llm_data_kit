"""
LLM API client for generating questions from answers
"""

import requests
import json
import time
import re
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass

@dataclass
class APIConfig:
    """Configuration for LLM API"""
    provider: str
    api_key: str
    base_url: str
    model: str
    max_tokens: int = 500
    temperature: float = 0.7

class LLMClient:
    """Client for interacting with various LLM APIs"""
    
    # Predefined API configurations
    API_CONFIGS = {
        'openrouter': {
            'base_url': 'https://openrouter.ai/api/v1/chat/completions',
            'default_model': 'deepseek/deepseek-chat-v3-0324:free',
        },
        'openai': {
            'base_url': 'https://api.openai.com/v1/chat/completions',
            'default_model': 'gpt-3.5-turbo',
        },
        'anthropic': {
            'base_url': 'https://api.anthropic.com/v1/messages',
            'default_model': 'claude-3-haiku-20240307',
        }
    }
    
    def __init__(self, config: APIConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json'
        })
        
        # Set authorization header based on provider
        if config.provider in ['openrouter', 'openai']:
            self.session.headers['Authorization'] = f'Bearer {config.api_key}'
            if config.provider == 'openrouter':
                # OpenRouter specific headers
                self.session.headers['HTTP-Referer'] = 'https://localhost'  # Required for some models
                self.session.headers['X-Title'] = 'LLama Fine-Tuning Tool'  # Optional app name
        elif config.provider == 'anthropic':
            self.session.headers['x-api-key'] = config.api_key
            self.session.headers['anthropic-version'] = '2023-06-01'
    
    def generate_question(self, answer: str, context: Optional[str] = None) -> str:
        """Generate a single question for an answer"""
        try:
            if self.config.provider == 'anthropic':
                return self._generate_question_anthropic(answer, context)
            else:
                return self._generate_question_openai_compatible(answer, context)
        
        except Exception as e:
            raise Exception(f"Failed to generate question: {str(e)}")
    
    def generate_questions_batch(self, 
                                answers: List[str], 
                                context: Optional[str] = None,
                                progress_callback: Optional[Callable[[int, int], None]] = None) -> List[Dict[str, str]]:
        """Generate questions for multiple answers with progress tracking"""
        results = []
        total = len(answers)
        
        for i, answer in enumerate(answers):
            try:
                question = self.generate_question(answer, context)
                results.append({
                    'question': question,
                    'answer': answer
                })
                
                if progress_callback:
                    progress_callback(i + 1, total)
                
                # Add small delay to avoid rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                # Log error but continue with next answer
                print(f"Error generating question for answer {i+1}: {e}")
                results.append({
                    'question': f"[Error generating question: {str(e)}]",
                    'answer': answer
                })
                
                if progress_callback:
                    progress_callback(i + 1, total)
        
        return results
    
    def _generate_question_openai_compatible(self, answer: str, context: Optional[str] = None) -> str:
        """Generate question using OpenAI-compatible API"""
        prompt = self._create_question_prompt(answer, context)
        
        payload = {
            'model': self.config.model,
            'messages': [
                {
                    'role': 'system',
                    'content': 'You are a helpful assistant that generates high-quality questions based on given answers. Create clear, specific questions that would naturally lead to the provided answer.'
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'max_tokens': self.config.max_tokens,
            'temperature': self.config.temperature
        }
        
        # Add OpenRouter specific headers if needed
        if self.config.provider == 'openrouter':
            payload['top_p'] = 1
            payload['frequency_penalty'] = 0
            payload['presence_penalty'] = 0
        
        response = self.session.post(self.config.base_url, json=payload, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        if 'choices' in data and data['choices']:
            return data['choices'][0]['message']['content'].strip()
        else:
            raise Exception("No valid response from API")
    
    def _generate_question_anthropic(self, answer: str, context: Optional[str] = None) -> str:
        """Generate question using Anthropic API"""
        prompt = self._create_question_prompt(answer, context)
        
        payload = {
            'model': self.config.model,
            'max_tokens': self.config.max_tokens,
            'messages': [
                {
                    'role': 'user',
                    'content': f"You are a helpful assistant that generates high-quality questions based on given answers. Create clear, specific questions that would naturally lead to the provided answer.\n\n{prompt}"
                }
            ]
        }
        
        response = self.session.post(self.config.base_url, json=payload, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        if 'content' in data and data['content']:
            return data['content'][0]['text'].strip()
        else:
            raise Exception("No valid response from API")
    
    def _create_question_prompt(self, answer: str, context: Optional[str] = None) -> str:
        """Create a prompt for question generation"""
        base_prompt = f"""Please generate a clear, specific question that would naturally lead to the following answer. The question should be:
- Clear and unambiguous
- Appropriate for the content and complexity of the answer
- Naturally answerable with the given text
- Not too broad or too narrow

Answer: "{answer}"

Please provide only the question, without any additional text or explanation."""
        
        if context:
            base_prompt = f"""Context: {context[:500]}...

{base_prompt}"""
        
        return base_prompt
    
    def test_connection(self) -> bool:
        """Test the API connection"""
        try:
            test_question = self.generate_question("This is a test answer.")
            return len(test_question.strip()) > 0
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False
    
    def debug_api_request(self) -> str:
        """Debug method to test API connectivity"""
        try:
            payload = {
                'model': self.config.model,
                'messages': [
                    {
                        'role': 'user',
                        'content': 'Hello, this is a test message. Please respond with "Connection successful".'
                    }
                ],
                'max_tokens': 50,
                'temperature': 0.1
            }
            
            print(f"Testing API connection...")
            print(f"URL: {self.config.base_url}")
            print(f"Model: {self.config.model}")
            print(f"Headers: {dict(self.session.headers)}")
            
            response = self.session.post(self.config.base_url, json=payload, timeout=30)
            print(f"Response status: {response.status_code}")
            print(f"Response text: {response.text[:1000]}")
            
            if response.status_code == 200:
                return "Connection successful"
            else:
                return f"Failed with status {response.status_code}: {response.text}"
                
        except Exception as e:
            return f"Debug request failed: {str(e)}"
    
    @classmethod
    def get_available_providers(cls) -> List[str]:
        """Get list of available API providers"""
        return list(cls.API_CONFIGS.keys())
    
    @classmethod
    def get_default_model(cls, provider: str) -> str:
        """Get default model for a provider"""
        return cls.API_CONFIGS.get(provider, {}).get('default_model', 'gpt-3.5-turbo')
    
    @classmethod
    def get_base_url(cls, provider: str) -> str:
        """Get base URL for a provider"""
        return cls.API_CONFIGS.get(provider, {}).get('base_url', 'https://api.openai.com/v1/chat/completions')
    
    def extract_qa_pairs_from_text(self, 
                                  text_chunk: str, 
                                  max_pairs: int = 25,
                                  retry_attempts: int = 3) -> List[Dict[str, str]]:
        """Extract Q&A pairs from a text chunk using AI"""
        
        for attempt in range(retry_attempts):
            try:
                if self.config.provider == 'anthropic':
                    return self._extract_qa_anthropic(text_chunk, max_pairs)
                else:
                    return self._extract_qa_openai_compatible(text_chunk, max_pairs)
                    
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    # Rate limited - wait and retry
                    wait_time = (2 ** attempt) * 5  # Exponential backoff: 5s, 10s, 20s
                    print(f"Rate limited. Waiting {wait_time}s before retry {attempt + 1}/{retry_attempts}")
                    time.sleep(wait_time)
                    continue
                else:
                    raise e
            except Exception as e:
                if attempt == retry_attempts - 1:
                    raise e
                time.sleep(2)  # Brief pause before retry
        
        return []
    
    def _extract_qa_openai_compatible(self, text_chunk: str, max_pairs: int) -> List[Dict[str, str]]:
        """Extract Q&A pairs using OpenAI-compatible API"""
        prompt = self._create_qa_extraction_prompt(text_chunk, max_pairs)
        
        payload = {
            'model': self.config.model,
            'messages': [
                {
                    'role': 'system',
                    'content': 'You are an expert at extracting question-answer pairs from text for training language models. Extract high-quality, factual Q&A pairs where answers are exact quotes from the provided text.'
                },
                {
                    'role': 'user', 
                    'content': prompt
                }
            ],
            'max_tokens': min(self.config.max_tokens * 2, 1500),  # Increase for Q&A extraction
            'temperature': 0.3  # Lower temperature for more consistent extraction
        }
        
        if self.config.provider == 'openrouter':
            payload['top_p'] = 1
            payload['frequency_penalty'] = 0
            payload['presence_penalty'] = 0
        
        try:
            response = self.session.post(self.config.base_url, json=payload, timeout=60)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            error_detail = f"HTTP {e.response.status_code}: {e.response.text[:500]}"
            raise Exception(f"API request failed - {error_detail}")
        
        data = response.json()
        
        if 'choices' in data and data['choices']:
            response_text = data['choices'][0]['message']['content'].strip()
            return self._parse_qa_response(response_text)
        else:
            raise Exception("No valid response from API")
    
    def _extract_qa_anthropic(self, text_chunk: str, max_pairs: int) -> List[Dict[str, str]]:
        """Extract Q&A pairs using Anthropic API"""
        prompt = self._create_qa_extraction_prompt(text_chunk, max_pairs)
        
        payload = {
            'model': self.config.model,
            'max_tokens': min(self.config.max_tokens * 2, 1500),
            'messages': [
                {
                    'role': 'user',
                    'content': f"You are an expert at extracting question-answer pairs from text for training language models. Extract high-quality, factual Q&A pairs where answers are exact quotes from the provided text.\n\n{prompt}"
                }
            ]
        }
        
        try:
            response = self.session.post(self.config.base_url, json=payload, timeout=60)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            error_detail = f"HTTP {e.response.status_code}: {e.response.text[:500]}"
            raise Exception(f"API request failed - {error_detail}")
        
        data = response.json()
        
        if 'content' in data and data['content']:
            response_text = data['content'][0]['text'].strip()
            return self._parse_qa_response(response_text)
        else:
            raise Exception("No valid response from API")
    
    def _create_qa_extraction_prompt(self, text_chunk: str, max_pairs: int) -> str:
        """Create prompt for Q&A extraction"""
        return f"""Extract up to {max_pairs} high-quality question-answer pairs from the following text. 

REQUIREMENTS:
1. Answers must be EXACT quotes from the provided text (no paraphrasing)
2. Questions should be clear, specific, and naturally lead to the answer
3. Focus on factual information, definitions, explanations, and key concepts
4. Avoid yes/no questions - prefer questions that require detailed answers
5. Ensure questions are varied in type (what, how, why, when, where, etc.)

FORMAT: Return ONLY a JSON array like this:
[
  {{"question": "What is...", "answer": "exact text from passage"}},
  {{"question": "How does...", "answer": "exact text from passage"}}
]

TEXT TO ANALYZE:
{text_chunk[:4000]}

Return only the JSON array, no additional text."""
    
    def _parse_qa_response(self, response_text: str) -> List[Dict[str, str]]:
        """Parse LLM response into Q&A pairs"""
        try:
            # First, try to extract JSON from markdown code blocks (```json ... ```)
            json_code_block_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', response_text, re.DOTALL | re.IGNORECASE)
            if json_code_block_match:
                json_str = json_code_block_match.group(1)
            else:
                # Fallback: Try to extract raw JSON array from response
                json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    # No JSON found, try fallback parsing
                    return self._parse_fallback_format(response_text)
            
            # Parse the JSON
            qa_pairs = json.loads(json_str)
            
            # Validate and clean the pairs
            validated_pairs = []
            for pair in qa_pairs:
                if isinstance(pair, dict) and 'question' in pair and 'answer' in pair:
                    question = pair['question'].strip()
                    answer = pair['answer'].strip()
                    
                    # Basic validation
                    if len(question) > 10 and len(answer) > 20:
                        validated_pairs.append({
                            'question': question,
                            'answer': answer
                        })
            
            return validated_pairs
                
        except json.JSONDecodeError:
            # Fallback parsing
            return self._parse_fallback_format(response_text)
    
    def _parse_fallback_format(self, response_text: str) -> List[Dict[str, str]]:
        """Fallback parser for non-JSON responses"""
        pairs = []
        lines = response_text.split('\n')
        
        current_q = None
        current_a = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Look for question patterns
            if any(line.lower().startswith(prefix) for prefix in ['q:', 'question:', 'q.', '?']):
                if current_q and current_a:
                    pairs.append({'question': current_q, 'answer': current_a})
                current_q = re.sub(r'^(q[:.]?\s*|question[:.]?\s*)', '', line, flags=re.IGNORECASE).strip()
                current_a = None
                
            # Look for answer patterns  
            elif any(line.lower().startswith(prefix) for prefix in ['a:', 'answer:', 'a.']):
                current_a = re.sub(r'^(a[:.]?\s*|answer[:.]?\s*)', '', line, flags=re.IGNORECASE).strip()
                
            # Continue building current answer
            elif current_q and not current_a:
                current_a = line
            elif current_a and line:
                current_a += ' ' + line
        
        # Add the last pair
        if current_q and current_a:
            pairs.append({'question': current_q, 'answer': current_a})
        
        return pairs