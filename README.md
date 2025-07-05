# LLM Data Kit

**Disclaimer:** This codebase was almost entirely written by Claude Sonnet 4, demonstrating the capabilities of AI-assisted software development for creating sophisticated desktop applications.

## Overview

A professional desktop application designed to create high-quality question-answer pairs from documents for fine-tuning large language models (LLMs). This tool provides a comprehensive workflow for processing documents, extracting answers, generating questions, and exporting training data in multiple formats compatible with popular LLM fine-tuning frameworks.

## Key Features

### Multiple Document Input Methods
- **Manual Selection**: Right-click in the document viewer to select text and add as answers
- **Automated Structure-Based Extraction**: Automatically identifies answers based on document structure (sentences, paragraphs, lists, definitions, facts, procedures)
- **AI-Powered Q&A Generation**: Uses LLM models to generate complete question-answer pairs directly from document chunks

### Document Processing
- **Large File Support**: Optimized for documents over 5MB with lazy loading and chunked processing
- **Multiple Formats**: Supports PDF, TXT, and Markdown files
- **Progress Tracking**: Real-time progress updates for all operations

### LLM Integration
- **Multi-Provider Support**: OpenRouter, OpenAI, and Anthropic APIs
- **Model Flexibility**: Support for various models including DeepSeek Chat V3, GPT-3.5/4, Claude 3, Llama 3.2, and other popular LLMs
- **Rate Limiting**: Intelligent exponential backoff for API quota management

## Installation

### Prerequisites
- Python 3.7 or higher
- pip package manager

### Dependencies
```bash
pip install -r requirements.txt
```

Required packages:
- PyPDF2==3.0.1
- pdfplumber==0.10.0
- requests==2.31.0
- tkinter-tooltip==2.1.0

## Getting Started

1. **Launch the Application**
   ```bash
   python main.py
   ```

2. **Configure API Settings**
   - Edit `api_config.json` with your LLM provider credentials
   - Currently configured for OpenRouter with DeepSeek Chat V3 model

3. **Load a Document**
   - Use File → Open Document to load PDF, TXT, or MD files
   - The application will open maximized with document viewer on the left

## Usage Workflows

### Method 1: Manual Answer Selection
1. Open your document in the viewer
2. Right-click on text passages to select them as answers
3. Selected text automatically appears in the answer manager
4. Generate questions for your answers using the question generator

### Method 2: Automated Structure-Based Extraction
1. Open your document
2. Click "Auto Extract" in the answer manager
3. Choose extraction methods:
   - **Sentences**: Extract complete sentences as answers
   - **Paragraphs**: Extract paragraph-level content
   - **Lists**: Identify and extract list items
   - **Definitions**: Find definition-style content
   - **Facts**: Extract factual statements
   - **Procedures**: Identify procedural content
4. Review and select from extracted candidates
5. Generate questions for approved answers

### Method 3: AI-Powered Q&A Generation
1. Open your document
2. Click "AI Extract" in the answer manager
3. Configure extraction settings:
   - Select LLM model
   - Adjust chunk size and overlap settings
   - Customize extraction prompts
4. The AI will process document chunks and generate complete Q&A pairs
5. Review and approve generated pairs

## Configuration

### API Configuration (`api_config.json`)
```json
{
  "provider": "openrouter",
  "api_key": "your-api-key-here",
  "model": "deepseek/deepseek-chat-v3-0324:free",
  "temperature": 0.3,
  "max_tokens": 1500
}
```

### Supported Models
- **OpenRouter**: DeepSeek Chat V3 (free), GPT-3.5/4, Claude 3, Llama 3.2
- **OpenAI**: GPT-3.5 Turbo, GPT-4
- **Anthropic**: Claude 3 Haiku

## Data Export

The application exports training data in multiple formats compatible with popular LLM fine-tuning frameworks:

### Supported Export Formats
- **OpenAI/ChatGPT Format**: JSON with message arrays for instruction-following fine-tuning
- **Alpaca Format**: Structured instruction-input-output format for instruction tuning
- **ShareGPT Format**: Conversation format with role-based messages
- **Hugging Face Datasets**: Compatible with transformers library and datasets
- **Custom JSON**: Flexible format with Q&A pairs and metadata
- **JSONL**: Line-delimited JSON for streaming and batch processing

### Export Features
- **Batch Export**: Export all Q&A pairs or selected subsets
- **Metadata Preservation**: Includes source document, extraction method, and generation parameters
- **Format Validation**: Ensures compatibility with target fine-tuning frameworks
- **Custom Templates**: Configurable output templates for specific use cases

## Known Limitations

- **API Compatibility**: Currently tested primarily with OpenRouter and a few select models. Some models and APIs may not work as expected
- **Rate Limiting**: Free tier models may have strict rate limits affecting batch processing
- **PDF Processing**: Complex PDF layouts may not parse perfectly in all cases

## Future Development

### Planned Features
- **Dark Theme**: Modern dark mode interface
- **Enhanced LLM Capabilities**: Improved client with better model support and configuration options
- **Advanced AI Interface**: More sophisticated AI extraction UI with better prompt management
- **Additional Input Sources**: Support for web scraping, API imports, and other document sources
- **Ready-Made Prompts**: Curated prompt templates for different use cases (academic, technical, creative, etc.)
- **Synthetic Data Kit Integration**: Research integration with synthetic data generation frameworks
