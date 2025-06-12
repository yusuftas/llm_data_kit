"""
Export dialog for saving training data in various formats
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

class ExportDialog:
    """Dialog for exporting training data"""
    
    def __init__(self, parent: tk.Widget, qa_pairs: List[Dict[str, str]]):
        self.parent = parent
        self.qa_pairs = qa_pairs
        self.result = None
        
        self.create_dialog()
    
    def create_dialog(self):
        """Create the export dialog"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Export Training Data")
        self.dialog.geometry("500x600")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.geometry("+%d+%d" % (
            self.parent.winfo_rootx() + 50,
            self.parent.winfo_rooty() + 50
        ))
        
        # Main frame
        main_frame = ttk.Frame(self.dialog, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="Export Training Data", font=('Arial', 14, 'bold'))
        title_label.pack(anchor=tk.W, pady=(0, 15))
        
        # Dataset info
        info_frame = ttk.LabelFrame(main_frame, text="Dataset Information", padding=10)
        info_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(info_frame, text=f"Total Q&A pairs: {len(self.qa_pairs)}").pack(anchor=tk.W)
        
        # Calculate statistics
        if self.qa_pairs:
            avg_q_len = sum(len(pair['question']) for pair in self.qa_pairs) / len(self.qa_pairs)
            avg_a_len = sum(len(pair['answer']) for pair in self.qa_pairs) / len(self.qa_pairs)
            ttk.Label(info_frame, text=f"Average question length: {avg_q_len:.0f} characters").pack(anchor=tk.W)
            ttk.Label(info_frame, text=f"Average answer length: {avg_a_len:.0f} characters").pack(anchor=tk.W)
        
        # Format selection
        format_frame = ttk.LabelFrame(main_frame, text="Export Format", padding=10)
        format_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.format_var = tk.StringVar(value="llama_jsonl")
        
        formats = [
            ("LLama JSONL (Recommended)", "llama_jsonl"),
            ("Alpaca JSON", "alpaca_json"),
            ("ShareGPT JSON", "sharegpt_json"),
            ("Custom JSONL", "custom_jsonl")
        ]
        
        for text, value in formats:
            ttk.Radiobutton(format_frame, text=text, variable=self.format_var, value=value).pack(anchor=tk.W, pady=2)
        
        # Options frame
        options_frame = ttk.LabelFrame(main_frame, text="Export Options", padding=10)
        options_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.include_metadata_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Include metadata", variable=self.include_metadata_var).pack(anchor=tk.W)
        
        self.shuffle_data_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Shuffle data", variable=self.shuffle_data_var).pack(anchor=tk.W)
        
        self.validate_data_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Validate data before export", variable=self.validate_data_var).pack(anchor=tk.W)
        
        # Preview frame
        preview_frame = ttk.LabelFrame(main_frame, text="Format Preview", padding=10)
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        self.preview_text = tk.Text(
            preview_frame,
            wrap=tk.WORD,
            font=('Courier', 9),
            height=8,
            state=tk.DISABLED
        )
        
        preview_scrollbar = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=self.preview_text.yview)
        self.preview_text.configure(yscrollcommand=preview_scrollbar.set)
        
        preview_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.preview_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Update preview when format changes
        self.format_var.trace_add('write', self.update_preview)
        self.update_preview()
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="Export", command=self.export_data).pack(side=tk.RIGHT)
        
        # Bind events
        self.dialog.bind('<Escape>', lambda e: self.cancel())
        
        # Wait for dialog to close
        self.dialog.wait_window()
    
    def update_preview(self, *args):
        """Update the format preview"""
        if not self.qa_pairs:
            return
        
        format_type = self.format_var.get()
        sample_pair = self.qa_pairs[0]
        
        try:
            if format_type == "llama_jsonl":
                preview = self.format_llama_jsonl([sample_pair])
            elif format_type == "alpaca_json":
                preview = self.format_alpaca_json([sample_pair])
            elif format_type == "sharegpt_json":
                preview = self.format_sharegpt_json([sample_pair])
            elif format_type == "custom_jsonl":
                preview = self.format_custom_jsonl([sample_pair])
            else:
                preview = "Unknown format"
            
            # Update preview text
            self.preview_text.config(state=tk.NORMAL)
            self.preview_text.delete(1.0, tk.END)
            self.preview_text.insert(1.0, preview)
            self.preview_text.config(state=tk.DISABLED)
        
        except Exception as e:
            self.preview_text.config(state=tk.NORMAL)
            self.preview_text.delete(1.0, tk.END)
            self.preview_text.insert(1.0, f"Preview error: {str(e)}")
            self.preview_text.config(state=tk.DISABLED)
    
    def format_llama_jsonl(self, pairs: List[Dict[str, str]]) -> str:
        """Format data for LLama fine-tuning (JSONL)"""
        lines = []
        for pair in pairs:
            entry = {
                "messages": [
                    {"role": "user", "content": pair['question']},
                    {"role": "assistant", "content": pair['answer']}
                ]
            }
            lines.append(json.dumps(entry, ensure_ascii=False))
        return '\n'.join(lines)
    
    def format_alpaca_json(self, pairs: List[Dict[str, str]]) -> str:
        """Format data in Alpaca format"""
        data = []
        for pair in pairs:
            entry = {
                "instruction": pair['question'],
                "input": "",
                "output": pair['answer']
            }
            data.append(entry)
        
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    def format_sharegpt_json(self, pairs: List[Dict[str, str]]) -> str:
        """Format data in ShareGPT format"""
        data = []
        for pair in pairs:
            entry = {
                "conversations": [
                    {"from": "human", "value": pair['question']},
                    {"from": "gpt", "value": pair['answer']}
                ]
            }
            data.append(entry)
        
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    def format_custom_jsonl(self, pairs: List[Dict[str, str]]) -> str:
        """Format data in custom JSONL format"""
        lines = []
        for pair in pairs:
            entry = {
                "question": pair['question'],
                "answer": pair['answer']
            }
            lines.append(json.dumps(entry, ensure_ascii=False))
        return '\n'.join(lines)
    
    def validate_data(self) -> bool:
        """Validate the data before export"""
        if not self.qa_pairs:
            messagebox.showerror("Error", "No data to export")
            return False
        
        # Check for empty questions or answers
        empty_questions = sum(1 for pair in self.qa_pairs if not pair.get('question', '').strip())
        empty_answers = sum(1 for pair in self.qa_pairs if not pair.get('answer', '').strip())
        
        if empty_questions > 0 or empty_answers > 0:
            message = f"Found {empty_questions} empty questions and {empty_answers} empty answers.\n\nContinue with export?"
            if not messagebox.askyesno("Validation Warning", message):
                return False
        
        # Check for very short content
        short_questions = sum(1 for pair in self.qa_pairs if len(pair.get('question', '').strip()) < 10)
        short_answers = sum(1 for pair in self.qa_pairs if len(pair.get('answer', '').strip()) < 10)
        
        if short_questions > 5 or short_answers > 5:
            message = f"Found {short_questions} very short questions and {short_answers} very short answers.\n\nThis might affect training quality. Continue?"
            if not messagebox.askyesno("Quality Warning", message):
                return False
        
        return True
    
    def export_data(self):
        """Export the data to file"""
        if self.validate_data_var.get() and not self.validate_data():
            return
        
        format_type = self.format_var.get()
        
        # File extension based on format
        if format_type in ["llama_jsonl", "custom_jsonl"]:
            default_ext = ".jsonl"
            file_types = [("JSONL files", "*.jsonl"), ("All files", "*.*")]
        else:
            default_ext = ".json"
            file_types = [("JSON files", "*.json"), ("All files", "*.*")]
        
        # Get file path
        file_path = filedialog.asksaveasfilename(
            title="Export Training Data",
            defaultextension=default_ext,
            filetypes=file_types,
            initialname=f"llama_training_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}{default_ext}"
        )
        
        if not file_path:
            return
        
        try:
            # Prepare data
            export_pairs = self.qa_pairs[:]
            
            if self.shuffle_data_var.get():
                import random
                random.shuffle(export_pairs)
            
            # Format data
            if format_type == "llama_jsonl":
                content = self.format_llama_jsonl(export_pairs)
            elif format_type == "alpaca_json":
                content = self.format_alpaca_json(export_pairs)
            elif format_type == "sharegpt_json":
                content = self.format_sharegpt_json(export_pairs)
            elif format_type == "custom_jsonl":
                content = self.format_custom_jsonl(export_pairs)
            else:
                raise ValueError(f"Unknown format: {format_type}")
            
            # Add metadata if requested
            if self.include_metadata_var.get() and format_type.endswith('_json'):
                # For JSON formats, wrap in metadata
                metadata = {
                    "metadata": {
                        "export_date": datetime.now().isoformat(),
                        "total_pairs": len(export_pairs),
                        "format": format_type,
                        "source": "LLama Fine-tuning UI Tool"
                    },
                    "data": json.loads(content)
                }
                content = json.dumps(metadata, indent=2, ensure_ascii=False)
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.result = file_path
            messagebox.showinfo("Success", f"Training data exported successfully!\n\nFile: {file_path}\nPairs: {len(export_pairs)}")
            self.dialog.destroy()
        
        except Exception as e:
            messagebox.showerror("Error", f"Export failed:\n{str(e)}")
    
    def cancel(self):
        """Cancel the export"""
        self.result = None
        self.dialog.destroy()