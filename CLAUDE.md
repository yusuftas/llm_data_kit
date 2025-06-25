# LLama Fine-Tuning Data Preparation Tool - Project Summary

## Overview
This is a Python desktop application designed to create high-quality question-answer pairs from documents for fine-tuning LLama 3.2 models. The application provides a user-friendly GUI for processing documents, extracting answers, generating questions, and exporting training data.

## Core Purpose
- **Primary Goal**: Generate training datasets for LLama 3.2 fine-tuning
- **Input**: PDF, text, and markdown documents
- **Output**: Question-answer pairs in LLama-compatible format
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
- **LLama Format**: Exports in format compatible with LLama fine-tuning
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
- **Current Setup**: OpenRouter with DeepSeek Chat V3 model (deepseek/deepseek-chat-v3:free)

## File Structure
```
llama_finetuning_ui/
├── main.py                    # Application entry point
├── requirements.txt           # Python dependencies
├── api_config.json           # LLM API configuration
├── core/                     # Core business logic
│   ├── document_parser.py    # Document processing
│   ├── answer_extractor.py   # Answer extraction
│   └── llm_client.py        # LLM API client
├── ui/                       # User interface
│   ├── main_window.py        # Main application window
│   ├── answer_manager.py     # Answer management
│   ├── document_viewer.py    # Document display
│   ├── question_generator.py # Question generation UI
│   ├── export_dialog.py      # Export configuration
│   └── auto_extraction_dialog.py # Auto-extraction UI
├── utils/                    # Utility functions (empty)
└── config/                   # Configuration files (empty)
```

## Current State
Based on git status, recent changes include:
- Optimized document parser for large files
- Enhanced answer extraction with multiple methods including AI mode
- AI-powered Q&A pair extraction using DeepSeek Chat V3 model
- Improved main window with proper viewer initialization
- Streamlined UI components removing older versions
- Rate limiting and error handling for API requests

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

### AI Extraction Mode
- **New Feature**: Added AI-powered Q&A pair extraction mode
- **Model**: Uses DeepSeek Chat V3 (deepseek/deepseek-chat-v3:free) via OpenRouter
- **Functionality**: Processes documents chunk-by-chunk to generate complete Q&A pairs
- **Integration**: Automatically adds answers to answer manager and questions to Q&A generator
- **Benefits**: Faster dataset creation with high-quality, contextually appropriate questions

### Technical Improvements
- **Rate Limiting**: Exponential backoff for API quota management (handles 429 errors)
- **Error Handling**: Enhanced error reporting and API connectivity debugging
- **Model Flexibility**: Support for multiple LLM providers with easy model switching
- **Performance**: Optimized for large documents with progress tracking