"""
AI extraction dialog for generating Q&A pairs with advanced configuration
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from typing import Dict, Any, List, Optional
import threading
import json
import requests
import time

from core.answer_extractor import AnswerExtractor, AnswerCandidate, ExtractionProgress
from core.llm_client import LLMClient, APIConfig


class AIExtractionDialog:
    """Dialog for AI-powered Q&A pair extraction with advanced configuration"""
    
    # Popular OpenRouter models with descriptions
    POPULAR_MODELS = [
        {"id": "deepseek/deepseek-chat-v3-0324:free", "name": "DeepSeek Chat V3 (Free)", "description": "High-quality free model"},
        {"id": "openai/gpt-3.5-turbo", "name": "GPT-3.5 Turbo", "description": "Fast and reliable"},
        {"id": "openai/gpt-4", "name": "GPT-4", "description": "Most capable but expensive"},
        {"id": "anthropic/claude-3-haiku-20240307", "name": "Claude 3 Haiku", "description": "Fast and efficient"},
        {"id": "meta-llama/llama-3.2-3b-instruct:free", "name": "Llama 3.2 3B (Free)", "description": "Free open-source model"},
        {"id": "meta-llama/llama-3.2-1b-instruct:free", "name": "Llama 3.2 1B (Free)", "description": "Lightweight free model"},
        {"id": "google/gemma-2-9b-it:free", "name": "Gemma 2 9B (Free)", "description": "Google's free model"}
    ]
    
    def __init__(self, parent: tk.Widget, document_data: Dict[str, Any], api_config: Dict[str, Any]):
        self.parent = parent
        self.document_data = document_data
        self.api_config = api_config
        self.result = None
        self.candidates = []
        self.ai_qa_pairs = []
        
        # Extraction state
        self.extractor = AnswerExtractor()
        self.extraction_thread = None
        self.is_extracting = False
        
        # Available models (will be populated)
        self.available_models = self.POPULAR_MODELS.copy()
        
        self.create_dialog()
    
    def create_dialog(self):
        """Create the AI extraction dialog"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("AI Q&A Extraction")
        
        # Dialog dimensions
        dialog_width = 800
        dialog_height = 750
        
        self.dialog.minsize(dialog_width, dialog_height)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.update_idletasks()
        screen_width = self.dialog.winfo_screenwidth()
        screen_height = self.dialog.winfo_screenheight()
        x = (screen_width - dialog_width) // 2
        y = (screen_height - dialog_height) // 2
        self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        
        # Main frame
        main_frame = ttk.Frame(self.dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="AI Q&A Extraction", font=('Arial', 12, 'bold'))
        title_label.pack(anchor=tk.W, pady=(0, 10))
        
        # Create configuration section
        self.create_config_section(main_frame)
        
        # Create extraction options
        self.create_extraction_options(main_frame)
        
        # Create results section
        self.create_results_section(main_frame)
        
        # Create progress section
        self.create_progress_section(main_frame)
        
        # Create button section
        self.create_buttons(main_frame)
        
        # Load models in background
        self.load_models_async()
        
        # Bind events
        self.dialog.bind('<Escape>', lambda e: self.cancel())
        self.dialog.protocol("WM_DELETE_WINDOW", self.cancel)
        
        # Wait for dialog to close
        self.dialog.wait_window()
    
    def create_config_section(self, parent):
        """Create model and API configuration section"""
        config_frame = ttk.LabelFrame(parent, text="Model Configuration", padding=10)
        config_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Model selection row
        model_frame = ttk.Frame(config_frame)
        model_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(model_frame, text="Model:").pack(side=tk.LEFT)
        
        self.model_var = tk.StringVar(value=self.api_config.get('model', 'deepseek/deepseek-chat-v3-0324:free'))
        self.model_combo = ttk.Combobox(model_frame, textvariable=self.model_var, width=90, state="readonly")
        self.model_combo.pack(side=tk.LEFT, padx=(5, 5))
        
        # Refresh models button
        refresh_btn = ttk.Button(model_frame, text="🔄", command=self.refresh_models, width=3)
        refresh_btn.pack(side=tk.LEFT, padx=(5, 0))
        
        # Temperature control
        temp_frame = ttk.Frame(config_frame)
        temp_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(temp_frame, text="Temperature:").pack(side=tk.LEFT)
        
        self.temperature_var = tk.DoubleVar(value=self.api_config.get('temperature', 0.3))
        temp_scale = ttk.Scale(temp_frame, from_=0.0, to=1.0, variable=self.temperature_var, 
                              orient=tk.HORIZONTAL, length=200)
        temp_scale.pack(side=tk.LEFT, padx=(5, 5))
        
        self.temp_label = ttk.Label(temp_frame, text="0.30")
        self.temp_label.pack(side=tk.LEFT)
        
        # Update temperature label when scale changes
        temp_scale.configure(command=lambda val: self.temp_label.config(text=f"{float(val):.2f}"))
        
        # Max tokens (moved next to temperature)
        tokens_frame = ttk.Frame(config_frame)
        tokens_frame.pack(fill=tk.X)
        
        ttk.Label(tokens_frame, text="Max Tokens:").pack(side=tk.LEFT)
        
        self.max_tokens_var = tk.StringVar(value=str(self.api_config.get('max_tokens', 1500)))
        tokens_entry = ttk.Entry(tokens_frame, textvariable=self.max_tokens_var, width=10)
        tokens_entry.pack(side=tk.LEFT, padx=(5, 0))
        
        # Populate initial model list
        self.update_model_combo()
    
    def create_extraction_options(self, parent):
        """Create extraction options section"""
        options_frame = ttk.LabelFrame(parent, text="Extraction Options", padding=10)
        options_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Chunk range
        chunk_frame = ttk.Frame(options_frame)
        chunk_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(chunk_frame, text="Chunk Range:").pack(side=tk.LEFT)
        
        metadata = self.document_data.get('metadata', {})
        total_chunks = metadata.get('chunk_count', 1)
        
        self.start_chunk_var = tk.StringVar(value="1")
        start_entry = ttk.Entry(chunk_frame, textvariable=self.start_chunk_var, width=6)
        start_entry.pack(side=tk.LEFT, padx=(5, 3))
        
        ttk.Label(chunk_frame, text="to").pack(side=tk.LEFT, padx=(0, 3))
        
        self.end_chunk_var = tk.StringVar(value=str(total_chunks))
        end_entry = ttk.Entry(chunk_frame, textvariable=self.end_chunk_var, width=6)
        end_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Label(chunk_frame, text=f"(max: {total_chunks})", 
                 font=('Arial', 8), foreground='gray').pack(side=tk.LEFT, padx=(5, 0))
        
        # Max Q&A pairs per chunk (moved next to chunk range)
        ttk.Label(chunk_frame, text="Max Q&A pairs:").pack(side=tk.LEFT, padx=(20, 0))
        
        self.max_pairs_var = tk.StringVar(value="25")
        pairs_entry = ttk.Entry(chunk_frame, textvariable=self.max_pairs_var, width=6)
        pairs_entry.pack(side=tk.LEFT, padx=(5, 0))
        
        # Custom prompt section
        prompt_label = ttk.Label(options_frame, text="Custom Requirements (optional):", font=('Arial', 9, 'bold'))
        prompt_label.pack(anchor=tk.W, pady=(0, 5))
        
        # Explanation
        explanation_label = ttk.Label(options_frame, 
                                    text="Customize the requirements for Q&A extraction.",
                                    font=('Arial', 8), foreground='gray')
        explanation_label.pack(anchor=tk.W, pady=(0, 5))
        
        self.prompt_text = scrolledtext.ScrolledText(options_frame, height=6, wrap=tk.WORD, font=('Arial', 9))
        self.prompt_text.pack(fill=tk.X, pady=(0, 10))
        
        # Default requirements (simplified)
        default_requirements = """REQUIREMENTS:
1. Answers must be EXACT quotes from the provided text (no paraphrasing)
2. Questions should be clear, specific, and naturally lead to the answer
3. Focus on factual information, definitions, explanations, and key concepts
4. Avoid yes/no questions - prefer questions that require detailed answers
5. Ensure questions are varied in type (what, how, why, when, where, etc.)"""
        
        self.prompt_text.insert(1.0, default_requirements)
        
        # Reset prompt button
        reset_btn = ttk.Button(options_frame, text="Reset to Default", 
                              command=lambda: self.reset_prompt(default_requirements))
        reset_btn.pack(anchor=tk.W)
    
    def create_results_section(self, parent):
        """Create results display section"""
        results_frame = ttk.LabelFrame(parent, text="Extraction Results", padding=5)
        results_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Results list with scrollbar
        list_frame = ttk.Frame(results_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ('Question', 'Answer Preview')
        self.results_tree = ttk.Treeview(list_frame, columns=columns, show='tree headings', height=6)
        
        self.results_tree.heading('#0', text='Select')
        self.results_tree.heading('Question', text='Question')
        self.results_tree.heading('Answer Preview', text='Answer Preview')
        
        self.results_tree.column('#0', width=60)
        self.results_tree.column('Question', width=300)
        self.results_tree.column('Answer Preview', width=300)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Selection controls
        selection_frame = ttk.Frame(results_frame)
        selection_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(selection_frame, text="Select All", command=self.select_all).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(selection_frame, text="Select None", command=self.select_none).pack(side=tk.LEFT, padx=(0, 5))
        
        self.selection_count_label = ttk.Label(selection_frame, text="0 selected")
        self.selection_count_label.pack(side=tk.RIGHT)
        
        # Bind events
        self.results_tree.bind('<Button-1>', self.on_tree_click)
        self.results_tree.bind('<Double-Button-1>', self.on_tree_double_click)
        
        self.selected_indices = set()
    
    def create_progress_section(self, parent):
        """Create progress section"""
        self.progress_frame = ttk.LabelFrame(parent, text="Progress", padding=5)
        
        progress_inner = ttk.Frame(self.progress_frame)
        progress_inner.pack(fill=tk.X)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_inner, variable=self.progress_var, maximum=100, length=300)
        self.progress_bar.pack(side=tk.LEFT, padx=(0, 10))
        
        self.progress_label = ttk.Label(progress_inner, text="Ready")
        self.progress_label.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_btn = ttk.Button(progress_inner, text="Stop", command=self.stop_extraction, 
                                  state=tk.DISABLED, width=8)
        self.stop_btn.pack(side=tk.RIGHT)
    
    def create_buttons(self, parent):
        """Create dialog buttons"""
        button_frame = ttk.Frame(parent)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
        
        # Start extraction button
        self.extract_btn = ttk.Button(button_frame, text="Start AI Extraction", 
                                     command=self.start_extraction)
        self.extract_btn.pack(side=tk.LEFT)
        
        # Right side buttons
        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="Add Selected", command=self.add_selected).pack(side=tk.RIGHT)
    
    def load_models_async(self):
        """Load available models from OpenRouter API in background"""
        def load_models():
            try:
                response = requests.get("https://openrouter.ai/api/v1/models", timeout=10)
                if response.status_code == 200:
                    models_data = response.json()
                    if isinstance(models_data, dict) and 'data' in models_data:
                        models_list = models_data['data']
                    else:
                        models_list = models_data
                    
                    # Extract model info
                    api_models = []
                    for model in models_list:
                        if isinstance(model, dict) and 'id' in model:
                            name = model.get('name', model['id'])
                            description = model.get('description', '')
                            if len(description) > 50:
                                description = description[:47] + "..."
                            
                            api_models.append({
                                'id': model['id'],
                                'name': name,
                                'description': description
                            })
                    
                    # Update models list on main thread
                    self.dialog.after(0, lambda: self.update_available_models(api_models))
                    
            except Exception as e:
                print(f"Failed to load models from API: {e}")
        
        # Run in background thread
        threading.Thread(target=load_models, daemon=True).start()
    
    def update_available_models(self, api_models):
        """Update the available models list"""
        # Combine popular models with API models, removing duplicates
        all_models = self.POPULAR_MODELS.copy()
        
        for api_model in api_models:
            if not any(m['id'] == api_model['id'] for m in all_models):
                all_models.append(api_model)
        
        self.available_models = all_models
        self.update_model_combo()
    
    def update_model_combo(self):
        """Update the model combo box"""
        model_options = []
        for model in self.available_models:
            display_text = f"{model['name']} ({model['id']})"
            if model.get('description'):
                display_text += f" - {model['description']}"
            model_options.append(display_text)
        
        self.model_combo['values'] = model_options
        
        # Select current model if it exists
        current_model = self.model_var.get()
        for i, model in enumerate(self.available_models):
            if model['id'] == current_model:
                self.model_combo.current(i)
                break
    
    def refresh_models(self):
        """Refresh the models list"""
        self.load_models_async()
    
    def reset_prompt(self, default_requirements):
        """Reset requirements to default"""
        self.prompt_text.delete(1.0, tk.END)
        self.prompt_text.insert(1.0, default_requirements)
    
    def start_extraction(self):
        """Start AI extraction"""
        try:
            # Validate inputs
            try:
                start_chunk = int(self.start_chunk_var.get()) - 1
                end_chunk = int(self.end_chunk_var.get())
                max_pairs = int(self.max_pairs_var.get())
                max_tokens = int(self.max_tokens_var.get())
            except ValueError:
                messagebox.showerror("Error", "Please enter valid numbers for chunk range, max pairs, and max tokens")
                return
            
            # Get selected model ID
            model_id = None
            current_selection = self.model_combo.current()
            if current_selection >= 0:
                model_id = self.available_models[current_selection]['id']
            else:
                # Fallback to text value
                model_id = self.model_var.get()
            
            if not model_id:
                messagebox.showerror("Error", "Please select a model")
                return
            
            # Validate chunk range
            metadata = self.document_data.get('metadata', {})
            total_chunks = metadata.get('chunk_count', 1)
            
            if start_chunk < 0:
                start_chunk = 0
            if end_chunk > total_chunks:
                end_chunk = total_chunks
            if start_chunk >= end_chunk:
                messagebox.showerror("Error", "Invalid chunk range")
                return
            
            # Show progress
            self.progress_frame.pack(fill=tk.X, pady=(5, 0))
            self.is_extracting = True
            self.extract_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            
            # Clear previous results
            self.candidates = []
            self.ai_qa_pairs = []
            self.selected_indices.clear()
            self.update_results_display()
            
            # Create API config
            api_config = APIConfig(
                provider=self.api_config['provider'],
                api_key=self.api_config['api_key'],
                base_url=LLMClient.get_base_url(self.api_config['provider']),
                model=model_id,
                max_tokens=max_tokens,
                temperature=self.temperature_var.get()
            )
            
            # Build complete prompt with custom requirements
            custom_requirements = self.prompt_text.get(1.0, tk.END).strip()
            
            # Build full prompt with format and text sections
            if custom_requirements:
                full_prompt = f"""Extract up to {{max_pairs}} high-quality question-answer pairs from the following text.

{custom_requirements}

FORMAT: Return ONLY a JSON array like this:
[
  {{"question": "What is...", "answer": "exact text from passage"}},
  {{"question": "How does...", "answer": "exact text from passage"}}
]

TEXT TO ANALYZE:
{{text_chunk}}

Return only the JSON array, no additional text."""
            else:
                # Use default if no custom requirements
                full_prompt = """Extract up to {{max_pairs}} high-quality question-answer pairs from the following text.

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
{{text_chunk}}

Return only the JSON array, no additional text."""
            
            custom_prompt = full_prompt
            
            # Start extraction in thread
            chunk_range = {'start': start_chunk, 'end': end_chunk} if start_chunk != 0 or end_chunk != total_chunks else None
            
            self.extraction_thread = self.extractor.extract_answers_threaded(
                self.document_data,
                methods=['ai'],
                progress_callback=self.on_extraction_progress,
                completion_callback=self.on_extraction_complete,
                error_callback=self.on_extraction_error,
                max_candidates=5000,
                chunk_range=chunk_range,
                ai_config=api_config,
                ai_max_pairs=max_pairs,
                ai_custom_prompt=custom_prompt
            )
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start extraction: {str(e)}")
            self.reset_extraction_state()
    
    def on_extraction_progress(self, progress: ExtractionProgress):
        """Handle extraction progress"""
        if progress.error_message:
            self.on_extraction_error(progress.error_message)
            return
        
        if progress.total_chunks > 0:
            progress_percent = (progress.current_chunk / progress.total_chunks) * 100
            self.progress_var.set(progress_percent)
        
        self.progress_label.config(
            text=f"Chunk {progress.current_chunk}/{progress.total_chunks} ({progress.candidates_found} Q&A pairs)"
        )
    
    def on_extraction_complete(self, candidates: List[AnswerCandidate]):
        """Handle extraction completion"""
        self.candidates = candidates
        
        # Extract Q&A pairs
        self.ai_qa_pairs = []
        for candidate in candidates:
            if candidate.extraction_method == 'ai' and candidate.context:
                self.ai_qa_pairs.append({
                    'question': candidate.context,
                    'answer': candidate.text
                })
        
        self.update_results_display()
        self.progress_label.config(text=f"Complete - {len(self.ai_qa_pairs)} Q&A pairs extracted")
        self.reset_extraction_state()
    
    def on_extraction_error(self, error_message: str):
        """Handle extraction error"""
        messagebox.showerror("Extraction Error", f"AI extraction failed: {error_message}")
        self.progress_label.config(text="Extraction failed")
        self.reset_extraction_state()
    
    def stop_extraction(self):
        """Stop extraction"""
        self.extractor.stop_current_extraction()
    
    def reset_extraction_state(self):
        """Reset extraction UI state"""
        self.is_extracting = False
        self.extract_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
    
    def update_results_display(self):
        """Update results tree"""
        # Clear existing items
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        
        # Add Q&A pairs
        for i, qa_pair in enumerate(self.ai_qa_pairs):
            checkbox = '☑' if i in self.selected_indices else '☐'
            answer_preview = qa_pair['answer'][:100] + "..." if len(qa_pair['answer']) > 100 else qa_pair['answer']
            
            self.results_tree.insert('', 'end',
                text=checkbox,
                values=(qa_pair['question'], answer_preview)
            )
        
        self.update_selection_count()
    
    def on_tree_click(self, event):
        """Handle tree click for selection"""
        item = self.results_tree.identify_row(event.y)
        if item:
            children = self.results_tree.get_children()
            item_index = children.index(item)
            
            if item_index in self.selected_indices:
                self.selected_indices.remove(item_index)
                self.results_tree.item(item, text='☐')
            else:
                self.selected_indices.add(item_index)
                self.results_tree.item(item, text='☑')
            
            self.update_selection_count()
    
    def on_tree_double_click(self, event):
        """Handle tree double-click to show details"""
        item = self.results_tree.identify_row(event.y)
        if item:
            children = self.results_tree.get_children()
            item_index = children.index(item)
            
            if item_index < len(self.ai_qa_pairs):
                qa_pair = self.ai_qa_pairs[item_index]
                self.show_qa_details(qa_pair)
    
    def show_qa_details(self, qa_pair):
        """Show Q&A pair details"""
        detail_window = tk.Toplevel(self.dialog)
        detail_window.title("Q&A Pair Details")
        detail_window.geometry("700x500")
        detail_window.transient(self.dialog)
        
        frame = ttk.Frame(detail_window, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Question
        ttk.Label(frame, text="Question:", font=('Arial', 10, 'bold')).pack(anchor=tk.W)
        q_text = tk.Text(frame, wrap=tk.WORD, height=3, font=('Arial', 11))
        q_text.pack(fill=tk.X, pady=(5, 10))
        q_text.insert(1.0, qa_pair['question'])
        q_text.config(state=tk.DISABLED)
        
        # Answer
        ttk.Label(frame, text="Answer:", font=('Arial', 10, 'bold')).pack(anchor=tk.W)
        a_text = tk.Text(frame, wrap=tk.WORD, height=15, font=('Arial', 11))
        a_text.pack(fill=tk.BOTH, expand=True, pady=(5, 10))
        a_text.insert(1.0, qa_pair['answer'])
        a_text.config(state=tk.DISABLED)
        
        ttk.Button(frame, text="Close", command=detail_window.destroy).pack(pady=(5, 0))
    
    def select_all(self):
        """Select all Q&A pairs"""
        for i in range(len(self.ai_qa_pairs)):
            self.selected_indices.add(i)
        self.update_results_display()
    
    def select_none(self):
        """Deselect all Q&A pairs"""
        self.selected_indices.clear()
        self.update_results_display()
    
    def update_selection_count(self):
        """Update selection count label"""
        self.selection_count_label.config(text=f"{len(self.selected_indices)} selected")
    
    def add_selected(self):
        """Add selected Q&A pairs"""
        if not self.selected_indices:
            messagebox.showwarning("Warning", "No Q&A pairs selected")
            return
        
        selected_candidates = [self.candidates[i] for i in sorted(self.selected_indices) if i < len(self.candidates)]
        selected_qa_pairs = [self.ai_qa_pairs[i] for i in sorted(self.selected_indices) if i < len(self.ai_qa_pairs)]
        
        self.result = selected_candidates
        self.ai_qa_pairs = selected_qa_pairs
        self.dialog.destroy()
    
    def cancel(self):
        """Cancel dialog"""
        if self.is_extracting:
            self.stop_extraction()
        
        self.result = None
        self.dialog.destroy()