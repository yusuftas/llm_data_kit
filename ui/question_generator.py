"""
Question generator widget for creating questions from answers using LLM APIs
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
from typing import List, Dict, Callable, Optional
import json

from core.llm_client import LLMClient, APIConfig

class QuestionGenerator:
    """Widget for generating questions from answers using LLM APIs"""
    
    def __init__(self, parent: tk.Widget, generation_callback: Callable[[List[Dict[str, str]]], None]):
        self.parent = parent
        self.generation_callback = generation_callback
        self.qa_pairs = []
        self.llm_client = None
        self.api_config = None
        self.get_answers_callback = None  # Callback to get current answers from main window
        
        self.setup_ui()
        self.load_api_config()
    
    def setup_ui(self):
        """Set up the question generator UI"""
        # Main frame
        self.frame = ttk.LabelFrame(self.parent, text="Question Generator", padding=5)
        self.frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # API Configuration frame
        self.api_frame = ttk.LabelFrame(self.frame, text="API Configuration", padding=5)
        self.api_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Provider selection
        provider_frame = ttk.Frame(self.api_frame)
        provider_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(provider_frame, text="Provider:").pack(side=tk.LEFT)
        
        self.provider_var = tk.StringVar(value="openrouter")
        self.provider_combo = ttk.Combobox(
            provider_frame,
            textvariable=self.provider_var,
            values=LLMClient.get_available_providers(),
            state="readonly",
            width=15
        )
        self.provider_combo.pack(side=tk.LEFT, padx=(5, 10))
        self.provider_combo.bind('<<ComboboxSelected>>', self.on_provider_change)
        
        # Model selection
        ttk.Label(provider_frame, text="Model:").pack(side=tk.LEFT)
        
        self.model_var = tk.StringVar(value="openai/gpt-3.5-turbo")
        self.model_entry = ttk.Entry(provider_frame, textvariable=self.model_var, width=20)
        self.model_entry.pack(side=tk.LEFT, padx=(5, 10))
        
        # API Key
        key_frame = ttk.Frame(self.api_frame)
        key_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(key_frame, text="API Key:").pack(side=tk.LEFT)
        
        self.api_key_var = tk.StringVar()
        self.api_key_entry = ttk.Entry(key_frame, textvariable=self.api_key_var, show="*", width=30)
        self.api_key_entry.pack(side=tk.LEFT, padx=(5, 10), fill=tk.X, expand=True)
        
        self.test_btn = ttk.Button(key_frame, text="Test", command=self.test_api_connection)
        self.test_btn.pack(side=tk.RIGHT)
        
        self.save_config_btn = ttk.Button(key_frame, text="Save Config", command=self.save_api_config)
        self.save_config_btn.pack(side=tk.RIGHT, padx=(0, 5))
        
        # Generation controls
        self.control_frame = ttk.Frame(self.frame)
        self.control_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.generate_btn = ttk.Button(
            self.control_frame,
            text="Generate Questions",
            command=self.on_generate_clicked,
            state=tk.DISABLED
        )
        self.generate_btn.pack(side=tk.LEFT)
        
        self.stop_btn = ttk.Button(
            self.control_frame,
            text="Stop",
            command=self.stop_generation,
            state=tk.DISABLED
        )
        self.stop_btn.pack(side=tk.LEFT, padx=(5, 0))
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            self.control_frame,
            variable=self.progress_var,
            maximum=100,
            length=200
        )
        self.progress_bar.pack(side=tk.RIGHT, padx=(10, 0))
        
        self.progress_label = ttk.Label(self.control_frame, text="")
        self.progress_label.pack(side=tk.RIGHT, padx=(10, 5))
        
        # Q&A Pairs display
        self.qa_frame = ttk.LabelFrame(self.frame, text="Generated Q&A Pairs", padding=5)
        self.qa_frame.pack(fill=tk.BOTH, expand=True)
        
        # Q&A List with scrollbar
        self.qa_list_frame = ttk.Frame(self.qa_frame)
        self.qa_list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        self.qa_tree = ttk.Treeview(
            self.qa_list_frame,
            columns=('Question', 'Answer'),
            show='headings',
            height=8
        )
        
        self.qa_tree.heading('Question', text='Question')
        self.qa_tree.heading('Answer', text='Answer')
        self.qa_tree.column('Question', width=300)
        self.qa_tree.column('Answer', width=300)
        
        self.qa_scrollbar = ttk.Scrollbar(
            self.qa_list_frame,
            orient=tk.VERTICAL,
            command=self.qa_tree.yview
        )
        self.qa_tree.configure(yscrollcommand=self.qa_scrollbar.set)
        
        # Pack tree and scrollbar
        self.qa_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.qa_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Q&A controls
        self.qa_control_frame = ttk.Frame(self.qa_frame)
        self.qa_control_frame.pack(fill=tk.X)
        
        self.edit_qa_btn = ttk.Button(
            self.qa_control_frame,
            text="Edit Selected",
            command=self.edit_selected_qa,
            state=tk.DISABLED
        )
        self.edit_qa_btn.pack(side=tk.LEFT)
        
        self.delete_qa_btn = ttk.Button(
            self.qa_control_frame,
            text="Delete Selected",
            command=self.delete_selected_qa,
            state=tk.DISABLED
        )
        self.delete_qa_btn.pack(side=tk.LEFT, padx=(5, 0))
        
        self.clear_qa_btn = ttk.Button(
            self.qa_control_frame,
            text="Clear All",
            command=self.clear_qa_pairs
        )
        self.clear_qa_btn.pack(side=tk.RIGHT)
        
        self.count_label = ttk.Label(self.qa_control_frame, text="0 pairs")
        self.count_label.pack(side=tk.RIGHT, padx=(0, 10))
        
        # Bind events
        self.qa_tree.bind('<<TreeviewSelect>>', self.on_qa_selection_change)
        self.qa_tree.bind('<Double-Button-1>', self.edit_selected_qa)
        
        # Generation state
        self.generation_thread = None
        self.stop_generation_flag = False
    
    def on_provider_change(self, event=None):
        """Handle provider selection change"""
        provider = self.provider_var.get()
        default_model = LLMClient.get_default_model(provider)
        self.model_var.set(default_model)
    
    def test_api_connection(self):
        """Test the API connection"""
        if not self.api_key_var.get().strip():
            messagebox.showerror("Error", "Please enter an API key")
            return
        
        try:
            config = self.create_api_config()
            client = LLMClient(config)
            
            # Test with a simple question
            self.test_btn.config(text="Testing...", state=tk.DISABLED)
            self.parent.update()
            
            if client.test_connection():
                messagebox.showinfo("Success", "API connection successful!")
                self.llm_client = client
                self.api_config = config
                self.generate_btn.config(state=tk.NORMAL)
            else:
                messagebox.showerror("Error", "API connection failed")
        
        except Exception as e:
            messagebox.showerror("Error", f"API test failed:\n{str(e)}")
        
        finally:
            self.test_btn.config(text="Test", state=tk.NORMAL)
    
    def create_api_config(self) -> APIConfig:
        """Create API configuration from UI inputs"""
        provider = self.provider_var.get()
        return APIConfig(
            provider=provider,
            api_key=self.api_key_var.get().strip(),
            base_url=LLMClient.get_base_url(provider),
            model=self.model_var.get().strip(),
            max_tokens=500,
            temperature=0.7
        )
    
    def save_api_config(self):
        """Save API configuration to file"""
        try:
            config_data = {
                'provider': self.provider_var.get(),
                'model': self.model_var.get(),
                'api_key': self.api_key_var.get()
            }
            
            with open('api_config.json', 'w') as f:
                json.dump(config_data, f, indent=2)
            
            messagebox.showinfo("Success", "API configuration saved")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration:\n{str(e)}")
    
    def load_api_config(self):
        """Load API configuration from file"""
        try:
            with open('api_config.json', 'r') as f:
                config_data = json.load(f)
            
            self.provider_var.set(config_data.get('provider', 'openrouter'))
            self.model_var.set(config_data.get('model', 'openai/gpt-3.5-turbo'))
            self.api_key_var.set(config_data.get('api_key', ''))
        
        except FileNotFoundError:
            pass  # Config file doesn't exist yet
        except Exception as e:
            print(f"Failed to load API config: {e}")
    
    def set_get_answers_callback(self, callback: Callable[[], List[str]]):
        """Set callback to get current answers from main window"""
        self.get_answers_callback = callback
    
    def on_generate_clicked(self):
        """Handle generate button click - get answers and start generation"""
        if self.get_answers_callback:
            answers = self.get_answers_callback()
            if answers:
                self.generate_questions(answers)
            else:
                messagebox.showwarning("Warning", "No answers available. Add some answers first.")
        else:
            messagebox.showinfo("Info", "Please use Tools -> Generate Questions from the menu, or select text and add answers first.")
    
    def generate_questions(self, answers: List[str]):
        """Start question generation for given answers"""
        if not answers:
            messagebox.showwarning("Warning", "No answers to generate questions for")
            return
        
        if not self.llm_client:
            messagebox.showerror("Error", "Please configure and test API connection first")
            return
        
        self.start_generation(answers)
    
    def start_generation(self, answers: Optional[List[str]] = None):
        """Start the question generation process"""
        if self.generation_thread and self.generation_thread.is_alive():
            return
        
        if not self.llm_client:
            messagebox.showerror("Error", "Please configure and test API connection first")
            return
        
        # If no answers provided, ask user (this shouldn't happen in normal flow)
        if not answers:
            messagebox.showwarning("Warning", "No answers available for question generation")
            return
        
        self.stop_generation_flag = False
        self.generate_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.progress_var.set(0)
        self.progress_label.config(text="Starting...")
        
        # Start generation in separate thread
        self.generation_thread = threading.Thread(
            target=self._generate_questions_thread,
            args=(answers,)
        )
        self.generation_thread.daemon = True
        self.generation_thread.start()
    
    def _generate_questions_thread(self, answers: List[str]):
        """Thread function for generating questions"""
        try:
            def progress_callback(current: int, total: int):
                if self.stop_generation_flag:
                    return
                
                progress = (current / total) * 100
                self.progress_var.set(progress)
                self.progress_label.config(text=f"{current}/{total}")
                
            # Generate questions
            new_qa_pairs = self.llm_client.generate_questions_batch(
                answers,
                progress_callback=progress_callback
            )
            
            if not self.stop_generation_flag:
                # Update UI in main thread
                self.parent.after(0, self._generation_complete, new_qa_pairs)
            
        except Exception as e:
            if not self.stop_generation_flag:
                self.parent.after(0, self._generation_error, str(e))
    
    def _generation_complete(self, new_qa_pairs: List[Dict[str, str]]):
        """Handle successful generation completion"""
        self.qa_pairs.extend(new_qa_pairs)
        self.refresh_qa_display()
        self.generation_callback(self.qa_pairs)
        
        self.generate_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.progress_label.config(text="Complete")
        
        messagebox.showinfo("Success", f"Generated {len(new_qa_pairs)} question-answer pairs")
    
    def _generation_error(self, error_message: str):
        """Handle generation error"""
        self.generate_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.progress_label.config(text="Error")
        
        messagebox.showerror("Error", f"Question generation failed:\n{error_message}")
    
    def stop_generation(self):
        """Stop the generation process"""
        self.stop_generation_flag = True
        self.generate_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.progress_label.config(text="Stopped")
    
    def refresh_qa_display(self):
        """Refresh the Q&A pairs display"""
        # Clear existing items
        for item in self.qa_tree.get_children():
            self.qa_tree.delete(item)
        
        # Add Q&A pairs
        for i, pair in enumerate(self.qa_pairs):
            question = pair['question'][:100] + "..." if len(pair['question']) > 100 else pair['question']
            answer = pair['answer'][:100] + "..." if len(pair['answer']) > 100 else pair['answer']
            
            self.qa_tree.insert('', 'end', values=(question, answer))
        
        # Update count
        self.count_label.config(text=f"{len(self.qa_pairs)} pairs")
    
    def on_qa_selection_change(self, event=None):
        """Handle Q&A selection change"""
        selection = self.qa_tree.selection()
        if selection:
            self.edit_qa_btn.config(state=tk.NORMAL)
            self.delete_qa_btn.config(state=tk.NORMAL)
        else:
            self.edit_qa_btn.config(state=tk.DISABLED)
            self.delete_qa_btn.config(state=tk.DISABLED)
    
    def edit_selected_qa(self, event=None):
        """Edit selected Q&A pair"""
        selection = self.qa_tree.selection()
        if selection:
            item = selection[0]
            index = self.qa_tree.index(item)
            
            pair = self.qa_pairs[index]
            dialog = QAEditDialog(self.parent, pair['question'], pair['answer'])
            
            if dialog.result:
                self.qa_pairs[index] = dialog.result
                self.refresh_qa_display()
                self.generation_callback(self.qa_pairs)
    
    def delete_selected_qa(self):
        """Delete selected Q&A pair"""
        selection = self.qa_tree.selection()
        if selection:
            item = selection[0]
            index = self.qa_tree.index(item)
            
            if messagebox.askyesno("Confirm", "Delete selected Q&A pair?"):
                del self.qa_pairs[index]
                self.refresh_qa_display()
                self.generation_callback(self.qa_pairs)
    
    def clear_qa_pairs(self):
        """Clear all Q&A pairs"""
        if self.qa_pairs and messagebox.askyesno("Confirm", "Clear all Q&A pairs?"):
            self.qa_pairs = []
            self.refresh_qa_display()
            self.generation_callback(self.qa_pairs)

class QAEditDialog:
    """Dialog for editing Q&A pairs"""
    
    def __init__(self, parent: tk.Widget, question: str, answer: str):
        self.parent = parent
        self.result = None
        self.question = question
        self.answer = answer
        
        self.create_dialog()
    
    def create_dialog(self):
        """Create the dialog window"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Edit Q&A Pair")
        self.dialog.geometry("600x400")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.geometry("+%d+%d" % (
            self.parent.winfo_rootx() + 50,
            self.parent.winfo_rooty() + 50
        ))
        
        # Main frame
        main_frame = ttk.Frame(self.dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Question section
        ttk.Label(main_frame, text="Question:", font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=(0, 5))
        
        self.question_text = tk.Text(
            main_frame,
            wrap=tk.WORD,
            font=('Arial', 11),
            height=6
        )
        self.question_text.pack(fill=tk.X, pady=(0, 10))
        self.question_text.insert(1.0, self.question)
        
        # Answer section
        ttk.Label(main_frame, text="Answer:", font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=(0, 5))
        
        self.answer_text = tk.Text(
            main_frame,
            wrap=tk.WORD,
            font=('Arial', 11),
            height=8
        )
        self.answer_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        self.answer_text.insert(1.0, self.answer)
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        # Buttons
        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="Save", command=self.save).pack(side=tk.RIGHT)
        
        # Bind events
        self.dialog.bind('<Escape>', lambda e: self.cancel())
        
        # Focus on question text
        self.question_text.focus_set()
        
        # Wait for dialog to close
        self.dialog.wait_window()
    
    def save(self):
        """Handle Save button"""
        question = self.question_text.get(1.0, tk.END).strip()
        answer = self.answer_text.get(1.0, tk.END).strip()
        
        if question and answer:
            self.result = {
                'question': question,
                'answer': answer
            }
        
        self.dialog.destroy()
    
    def cancel(self):
        """Handle Cancel button"""
        self.result = None
        self.dialog.destroy()