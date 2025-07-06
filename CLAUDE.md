# LLM Data Kit - Fine-Tuning Data Preparation Tool

## Overview
This is a Python desktop application designed to create high-quality question-answer pairs from documents for fine-tuning LLM models. The application provides a user-friendly GUI for processing documents, extracting answers, generating questions, and exporting training data.

## Core Purpose
- **Primary Goal**: Generate training datasets for LLM fine-tuning (originally designed for LLama 3.2)
- **Input**: PDF, text, and markdown documents
- **Output**: Question-answer pairs in LLM-compatible format
- **Target Users**: ML engineers and researchers preparing fine-tuning datasets

## Architecture

### Main Components

#### 1. Entry Point (`main.py`)
- Simple launcher that initializes the Tkinter GUI
- Sets up Python path and launches MainWindow

#### 2. Core Modules (`core/`)

**Document Parser (`core/document_parser.py`)**
- Optimized for large files (>5MB) with lazy loading
- Supports PDF (PyPDF2/pdfplumber), TXT, and MD files
- Features chunked processing with progress callbacks
- Implements DocumentChunk and DocumentIndex classes for efficient memory usage
- Key methods: `parse_document_lazy()`, `load_chunk()`, `get_text_at_position()`

**Answer Extractor (`core/answer_extractor.py`)**
- Multi-method extraction: sentences, paragraphs, lists, definitions, facts, procedures, AI extraction
- AI extraction mode uses LLM to generate Q&A pairs directly from document chunks
- Progress tracking and threading support for large documents
- Confidence scoring for each extracted candidate
- Deduplication and filtering algorithms
- Key classes: `AnswerCandidate`, `ExtractionProgress`

**LLM Client (`core/llm_client.py`)**
- Multi-provider API support: OpenRouter, OpenAI, Anthropic
- Batch question generation with progress tracking
- AI-powered Q&A pair extraction from text chunks
- Rate limiting with exponential backoff for quota management
- Error handling and API connectivity debugging
- Configurable models and parameters

#### 3. UI Components (`ui/`)

**Main Window (`ui/main_window.py`)**
- Primary application interface with menu system
- Document loading and viewer integration
- Answer and Q&A pair management
- Export functionality with progress tracking
- Keyboard shortcuts and status updates

**Additional UI Modules**:
- `answer_manager.py`: Answer list management and editing
- `auto_extraction_dialog.py`: Automated answer extraction interface
- `ai_extraction_dialog.py`: Advanced AI-powered Q&A pair extraction with model selection
- `document_viewer.py`: Document display with text selection
- `export_dialog.py`: Training data export configurations
- `question_generator.py`: LLM-based question generation interface

### Key Features

#### Document Processing
- **Lazy Loading**: Processes large documents without loading entire content into memory
- **Chunked Processing**: Divides documents into manageable chunks for efficient processing
- **Progress Tracking**: Real-time progress updates for all operations
- **Multiple Formats**: PDF, TXT, MD support with fallback parsing

#### Answer Extraction
- **Multi-Method Extraction**: 7 different extraction strategies (including AI mode)
- **AI Extraction**: Uses LLM to generate complete Q&A pairs from document chunks
- **Confidence Scoring**: Each candidate rated for quality
- **Overlap Detection**: Removes duplicate or overlapping candidates
- **Filtering**: Length, confidence, and content quality filters

#### Question Generation
- **LLM Integration**: Uses multiple LLM providers for question generation
- **Batch Processing**: Generates questions for multiple answers efficiently
- **Error Handling**: Graceful handling of API failures
- **Rate Limiting**: Prevents API overuse

#### Data Export
- **LLM Format**: Exports in format compatible with LLM fine-tuning
- **JSON Storage**: Save/load answer sets and Q&A pairs
- **Metadata Preservation**: Tracks document and generation metadata

## Technical Stack

### Dependencies
- **GUI**: Tkinter (built-in Python)
- **PDF Processing**: PyPDF2 (3.0.1), pdfplumber (0.10.0)
- **HTTP Requests**: requests (2.31.0)
- **UI Enhancement**: tkinter-tooltip (2.1.0)

### Configuration
- **API Config**: `api_config.json` stores LLM provider settings
- **Current Setup**: OpenRouter with DeepSeek Chat V3 model (deepseek/deepseek-chat-v3-0324:free)

## File Structure
```
llm_data_kit/
├── main.py                    # Application entry point
├── requirements.txt           # Python dependencies
├── api_config.json           # LLM API configuration
├── CLAUDE.md                 # Project documentation
├── LICENSE                   # Project license
├── README.md                 # Project readme
├── core/                     # Core business logic
│   ├── document_parser.py    # Document processing
│   ├── answer_extractor.py   # Answer extraction
│   └── llm_client.py        # LLM API client
└── ui/                       # User interface
    ├── main_window.py        # Main application window
    ├── answer_manager.py     # Answer management
    ├── document_viewer.py    # Document display
    ├── question_generator.py # Question generation UI
    ├── export_dialog.py      # Export configuration
    ├── auto_extraction_dialog.py # Auto-extraction UI
    └── ai_extraction_dialog.py   # AI-powered extraction UI
```

## Current State
Based on git status and recent commits, the project has undergone significant improvements:
- **Repository Name**: Changed from `llama_finetuning_ui` to `llm_data_kit` 
- **Recent Commits**: Latest work includes model selection improvements, UI tweaks, and documentation updates
- **Active Development**: Multiple files modified with focus on AI extraction dialog and LLM client enhancements
- **Documentation**: Added comprehensive README.md and LICENSE files for better project documentation

## Key Workflows

1. **Document Loading**: User opens document → Parser creates lazy-loaded structure → Viewer displays content
2. **Answer Selection**: User selects text → Added to answer manager → Displayed in answer list
3. **Auto-Extraction**: User triggers extraction → Multiple methods scan document → Candidates presented for selection
4. **AI Extraction**: User selects AI mode → LLM processes document chunks → Q&A pairs generated and integrated
5. **Question Generation**: User generates questions → LLM processes answers → Q&A pairs created
6. **Export**: User exports data → Training format generated → File saved for fine-tuning

## Performance Optimizations
- Lazy loading for large documents
- Chunked processing to manage memory
- Progress callbacks for user feedback
- Threading for non-blocking operations
- Caching mechanisms in document parser

## Development Notes
- Built with defensive coding practices
- Extensive error handling throughout
- Modular architecture for easy extension
- Support for multiple LLM providers
- Optimized for large document processing (>5MB)

This application represents a complete pipeline for preparing high-quality fine-tuning datasets from document sources, with particular attention to performance and user experience when working with large documents.

## Recent Updates

### AI Extraction Dialog Enhancement
- **Advanced UI**: New `ai_extraction_dialog.py` with sophisticated model selection interface
- **Model Selection**: Supports multiple popular models including DeepSeek Chat V3, GPT-3.5/4, Claude 3, and Llama 3.2
- **Free Models**: Focus on free model options like DeepSeek Chat V3 and Llama 3.2 variants
- **Model Discovery**: Automatic model list population from OpenRouter API
- **Configuration**: Advanced parameter tuning for chunk size, temperature, and max tokens

### Technical Improvements
- **Rate Limiting**: Exponential backoff for API quota management (handles 429 errors)
- **Error Handling**: Enhanced error reporting and API connectivity debugging
- **Model Flexibility**: Support for multiple LLM providers with easy model switching
- **Performance**: Optimized for large documents with progress tracking
- **UI/UX**: Improved dialog centering, maximized main window, and better visibility controls

### Development Status
- **Active Branch**: `main` with ongoing modifications to multiple files
- **Recent Focus**: AI extraction dialog improvements and model list enhancements
- **Code Quality**: Maintained defensive coding practices with comprehensive error handling