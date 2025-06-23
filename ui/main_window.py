"""
Fixed Main application window with proper viewer initialization
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional

from ui.answer_manager import AnswerManager
from ui.question_generator import QuestionGenerator
from ui.export_dialog import ExportDialog

# Try to import optimized components
from core.document_parser import DocumentParser
from ui.document_viewer import DocumentViewer

class MainWindow:
    """Main application window with fixed viewer initialization"""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("LLama 3.2 Fine-Tuning Data Preparation Tool")
        self.root.geometry("1200x800")
        
        # Initialize components
        self.document_parser = DocumentParser()
            
        self.current_document = None
        self.answers = []
        self.qa_pairs = []
        
        self.setup_ui()
        self.setup_menu()
    
    def setup_ui(self):
        """Set up the main user interface"""
        # Create main paned window
        self.main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel - Document viewer
        self.left_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(self.left_frame, weight=2)
        
        # Initialize document viewer (always start with regular viewer)
        self.document_viewer = DocumentViewer(self.left_frame, self.on_text_selected)
        
        # Right panel - Answer management and controls
        self.right_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(self.right_frame, weight=1)
        
        # Answer manager
        self.answer_manager = AnswerManager(self.right_frame, self.on_answer_modified)
        
        # Question generator
        self.question_generator = QuestionGenerator(self.right_frame, self.on_questions_generated)
        self.question_generator.set_get_answers_callback(lambda: self.answers)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def setup_menu(self):
        """Set up the application menu"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open Document...", command=self.open_document, accelerator="Ctrl+O")
        file_menu.add_separator()
        file_menu.add_command(label="Save Answers & Q&A Pairs...", command=self.save_answers, accelerator="Ctrl+S")
        file_menu.add_command(label="Load Answers & Q&A Pairs...", command=self.load_answers, accelerator="Ctrl+L")
        file_menu.add_separator()
        file_menu.add_command(label="Export Training Data...", command=self.export_training_data, accelerator="Ctrl+E")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Clear All Answers", command=self.clear_answers)
        edit_menu.add_command(label="Clear All Q&A Pairs", command=self.clear_qa_pairs)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Auto Extract Answers", command=self.auto_extract_answers)
        tools_menu.add_separator()
        tools_menu.add_command(label="Generate Questions", command=self.generate_questions)
        tools_menu.add_command(label="API Settings", command=self.show_api_settings)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
        
        # Keyboard shortcuts
        self.root.bind('<Control-o>', lambda e: self.open_document())
        self.root.bind('<Control-s>', lambda e: self.save_answers())
        self.root.bind('<Control-l>', lambda e: self.load_answers())
        self.root.bind('<Control-e>', lambda e: self.export_training_data())
    
    def open_document(self):
        """Open a document file"""
        file_types = [
            ("All Supported", "*.pdf;*.txt;*.md"),
            ("PDF files", "*.pdf"),
            ("Text files", "*.txt"),
            ("Markdown files", "*.md"),
            ("All files", "*.*")
        ]
        
        file_path = filedialog.askopenfilename(
            title="Open Document",
            filetypes=file_types
        )
        
        if file_path:
            try:
                self.status_var.set("Loading document...")
                self.root.update()
                
                if not self.document_parser.is_supported(file_path):
                    messagebox.showerror("Error", "Unsupported file format")
                    return
                
                # Check file size to determine which parser to use
                file_size = os.path.getsize(file_path)
                
                self.status_var.set("Loading large document (optimized mode)...")
                self.root.update()
                
                # Use optimized parser with progress callback
                def progress_callback(current, total):
                    if total > 0:
                        progress = (current / total) * 100
                        self.status_var.set(f"Loading document... {progress:.0f}%")
                        self.root.update()
                
                self.current_document = self.document_parser.parse_document_lazy(
                    file_path, progress_callback
                )
                
                # Load document into viewer
                self.document_viewer.load_document(self.current_document)
                self.answer_manager.set_current_document(self.current_document)
                
                file_name = os.path.basename(file_path)
                file_size_mb = file_size / (1024 * 1024)
                self.status_var.set(f"Loaded: {file_name} ({file_size_mb:.1f}MB")
                self.root.title(f"LLama Fine-Tuning Tool - {file_name}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load document:\n{str(e)}")
                self.status_var.set("Error loading document")
    
    def on_text_selected(self, selected_text: str, start_pos: int, end_pos: int):
        """Handle text selection from document viewer"""
        if selected_text.strip():
            self.answer_manager.add_answer(selected_text.strip())
            self.status_var.set(f"Added answer ({len(selected_text.strip())} characters)")
    
    def on_answer_modified(self, answers: List[str]):
        """Handle answer list modifications"""
        self.answers = answers
        self.status_var.set(f"Answers: {len(self.answers)}")
    
    def on_questions_generated(self, qa_pairs: List[Dict[str, str]]):
        """Handle generated questions"""
        print(f"Main window received {len(qa_pairs)} Q&A pairs")  # Debug
        self.qa_pairs = qa_pairs
        self.status_var.set(f"Generated {len(qa_pairs)} Q&A pairs")
    
    def save_answers(self):
        """Save current answers and Q&A pairs to file"""
        if not self.answers and not self.qa_pairs:
            messagebox.showwarning("Warning", "No answers or Q&A pairs to save")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Save Answers & Q&A Pairs",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                data = {
                    'answers': self.answers,
                    'qa_pairs': self.qa_pairs,
                    'document_info': self.current_document['metadata'] if self.current_document else None,
                    'saved_at': datetime.now().isoformat(),
                    'version': '1.0'
                }
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                self.status_var.set(f"Saved {len(self.answers)} answers and {len(self.qa_pairs)} Q&A pairs")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save data:\n{str(e)}")
    
    def load_answers(self):
        """Load answers and Q&A pairs from file"""
        file_path = filedialog.askopenfilename(
            title="Load Answers & Q&A Pairs",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Load answers
                if 'answers' in data:
                    self.answers = data['answers']
                    self.answer_manager.load_answers(self.answers)
                else:
                    self.answers = []
                
                # Load Q&A pairs if available
                if 'qa_pairs' in data:
                    self.qa_pairs = data['qa_pairs']
                    self.question_generator.load_qa_pairs(self.qa_pairs)
                else:
                    self.qa_pairs = []
                
                status_msg = f"Loaded {len(self.answers)} answers"
                if self.qa_pairs:
                    status_msg += f" and {len(self.qa_pairs)} Q&A pairs"
                
                self.status_var.set(status_msg)
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load data:\n{str(e)}")
    
    def export_training_data(self):
        """Export training data in LLama format"""
        print(f"Export called. QA pairs in main window: {len(self.qa_pairs)}")  # Debug
        if not self.qa_pairs:
            messagebox.showwarning("Warning", "No Q&A pairs to export. Generate questions first.")
            return
        
        dialog = ExportDialog(self.root, self.qa_pairs)
        if dialog.result:
            self.status_var.set("Training data exported successfully")
    
    def auto_extract_answers(self):
        """Auto-extract answers from current document"""
        if not self.current_document:
            messagebox.showwarning("Warning", "No document loaded. Please open a document first.")
            return
        
        self.answer_manager.show_auto_extract_dialog()
    
    def generate_questions(self):
        """Generate questions for current answers"""
        if not self.answers:
            messagebox.showwarning("Warning", "No answers available. Add some answers first.")
            return
        
        # Let the question generator handle the filtering based on skip setting
        self.question_generator.on_generate_clicked()
    
    def clear_answers(self):
        """Clear all answers"""
        if messagebox.askyesno("Confirm", "Clear all answers?"):
            self.answers = []
            self.answer_manager.clear_answers()
            self.status_var.set("Answers cleared")
    
    def clear_qa_pairs(self):
        """Clear all Q&A pairs"""
        if messagebox.askyesno("Confirm", "Clear all Q&A pairs?"):
            self.qa_pairs = []
            self.question_generator.clear_qa_pairs()
            self.status_var.set("Q&A pairs cleared")
    
    def show_api_settings(self):
        """Show API settings dialog"""
        # This will be implemented with the API settings dialog
        messagebox.showinfo("Info", "API Settings dialog will be implemented")
    
    def show_about(self):
        """Show about dialog"""
        about_text = """LLama 3.2 Fine-Tuning Data Preparation Tool
            A Python application for creating high-quality question-answer pairs 
            from documents to fine-tune LLama 3.2 models.

            Features:
            • Load PDF and text documents
            • Select text portions as answers
            • Generate questions using LLM APIs
            • Export in LLama-compatible format
        """
        
        about_text += "• Optimized for large documents (>5MB)\n"
        about_text += "• Lazy loading and pagination support\n"
        
        about_text += "\nVersion: 1.0.0"
        
        messagebox.showinfo("About", about_text)