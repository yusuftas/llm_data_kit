"""
LLM API client for generating questions from answers
"""

import requests
import json
import time
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
            'default_model': 'openai/gpt-3.5-turbo',
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
        except:
            return False
    
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