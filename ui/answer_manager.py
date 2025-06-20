"""
Answer management widget for organizing selected text answers
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Callable, Optional, Dict, Any
from core.answer_extractor import AnswerExtractor, AnswerCandidate

class AnswerManager:
    """Widget for managing selected answers"""
    
    def __init__(self, parent: tk.Widget, modification_callback: Callable[[List[str]], None]):
        self.parent = parent
        self.modification_callback = modification_callback
        self.answers = []
        self.current_document = None
        self.answer_extractor = AnswerExtractor()
        self.extraction_candidates = []
        
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the answer manager UI"""
        # Main frame
        self.frame = ttk.LabelFrame(self.parent, text="Answers", padding=5)
        self.frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Info frame
        self.info_frame = ttk.Frame(self.frame)
        self.info_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.count_label = ttk.Label(self.info_frame, text="0 answers")
        self.count_label.pack(side=tk.LEFT)
        
        # Control buttons frame
        self.button_frame = ttk.Frame(self.frame)
        self.button_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.add_manual_btn = ttk.Button(
            self.button_frame,
            text="Add Manual",
            command=self.add_manual_answer
        )
        self.add_manual_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.auto_extract_btn = ttk.Button(
            self.button_frame,
            text="Auto Extract",
            command=self.show_auto_extract_dialog,
            state=tk.DISABLED
        )
        self.auto_extract_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.edit_btn = ttk.Button(
            self.button_frame,
            text="Edit",
            command=self.edit_selected_answer,
            state=tk.DISABLED
        )
        self.edit_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.delete_btn = ttk.Button(
            self.button_frame,
            text="Delete",
            command=self.delete_selected_answer,
            state=tk.DISABLED
        )
        self.delete_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.clear_btn = ttk.Button(
            self.button_frame,
            text="Clear All",
            command=self.clear_all_answers
        )
        self.clear_btn.pack(side=tk.RIGHT)
        
        # Listbox with scrollbar
        self.list_frame = ttk.Frame(self.frame)
        self.list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.listbox = tk.Listbox(
            self.list_frame,
            selectmode=tk.SINGLE,
            font=('Arial', 10)
        )
        
        self.list_scrollbar = ttk.Scrollbar(
            self.list_frame,
            orient=tk.VERTICAL,
            command=self.listbox.yview
        )
        self.listbox.configure(yscrollcommand=self.list_scrollbar.set)
        
        # Pack listbox and scrollbar
        self.list_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Preview frame
        self.preview_frame = ttk.LabelFrame(self.frame, text="Preview", padding=5)
        self.preview_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.preview_text = tk.Text(
            self.preview_frame,
            height=4,
            wrap=tk.WORD,
            font=('Arial', 9),
            state=tk.DISABLED
        )
        self.preview_text.pack(fill=tk.X)
        
        # Bind events
        self.listbox.bind('<<ListboxSelect>>', self.on_selection_change)
        self.listbox.bind('<Double-Button-1>', self.edit_selected_answer)
    
    def add_answer(self, answer_text: str):
        """Add a new answer to the list"""
        if answer_text.strip():
            clean_answer = answer_text.strip()
            self.answers.append(clean_answer)
            self.refresh_list()
            self.modification_callback(self.answers)
            
            # Select the newly added item
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(len(self.answers) - 1)
            self.listbox.see(len(self.answers) - 1)
            self.on_selection_change()
    
    def add_manual_answer(self):
        """Add answer manually through dialog"""
        dialog = ManualAnswerDialog(self.parent)
        if dialog.result:
            self.add_answer(dialog.result)
    
    def edit_selected_answer(self, event=None):
        """Edit the selected answer"""
        selection = self.listbox.curselection()
        if selection:
            index = selection[0]
            current_answer = self.answers[index]
            
            dialog = ManualAnswerDialog(self.parent, current_answer)
            if dialog.result:
                self.answers[index] = dialog.result
                self.refresh_list()
                self.modification_callback(self.answers)
                
                # Maintain selection
                self.listbox.selection_set(index)
                self.on_selection_change()
    
    def delete_selected_answer(self):
        """Delete the selected answer"""
        selection = self.listbox.curselection()
        if selection:
            index = selection[0]
            answer_preview = self.answers[index][:50] + "..." if len(self.answers[index]) > 50 else self.answers[index]
            
            if messagebox.askyesno("Confirm Delete", f"Delete this answer?\n\n{answer_preview}"):
                del self.answers[index]
                self.refresh_list()
                self.modification_callback(self.answers)
                
                # Update button states
                self.edit_btn.config(state=tk.DISABLED)
                self.delete_btn.config(state=tk.DISABLED)
                self.preview_text.config(state=tk.NORMAL)
                self.preview_text.delete(1.0, tk.END)
                self.preview_text.config(state=tk.DISABLED)
    
    def clear_all_answers(self):
        """Clear all answers"""
        if self.answers and messagebox.askyesno("Confirm Clear", "Clear all answers?"):
            self.clear_answers()
    
    def clear_answers(self):
        """Clear answers without confirmation"""
        self.answers = []
        self.refresh_list()
        self.modification_callback(self.answers)
        
        # Update UI state
        self.edit_btn.config(state=tk.DISABLED)
        self.delete_btn.config(state=tk.DISABLED)
        self.preview_text.config(state=tk.NORMAL)
        self.preview_text.delete(1.0, tk.END)
        self.preview_text.config(state=tk.DISABLED)
    
    def load_answers(self, answers: List[str]):
        """Load answers from external source"""
        self.answers = answers[:]
        self.refresh_list()
        self.modification_callback(self.answers)
    
    def set_current_document(self, document_data: Dict[str, Any]):
        """Set the current document for auto-extraction"""
        self.current_document = document_data
        self.auto_extract_btn.config(state=tk.NORMAL if document_data else tk.DISABLED)
    
    def show_auto_extract_dialog(self):
        """Show auto-extraction dialog"""
        if not self.current_document:
            messagebox.showwarning("Warning", "No document loaded for extraction")
            return
        
        dialog = AutoExtractionDialog(self.parent, self.current_document, self.answer_extractor)
        if dialog.result:
            # Add selected candidates as answers
            for candidate in dialog.result:
                self.add_answer(candidate.text)
            
            messagebox.showinfo("Success", f"Added {len(dialog.result)} answers from auto-extraction")
    
    def refresh_list(self):
        """Refresh the listbox display"""
        self.listbox.delete(0, tk.END)
        
        for i, answer in enumerate(self.answers):
            # Create preview text (first 60 characters)
            preview = answer.replace('\n', ' ').replace('\r', ' ')
            if len(preview) > 60:
                preview = preview[:57] + "..."
            
            display_text = f"{i+1:2d}. {preview}"
            self.listbox.insert(tk.END, display_text)
        
        # Update count
        self.count_label.config(text=f"{len(self.answers)} answers")
    
    def on_selection_change(self, event=None):
        """Handle listbox selection change"""
        selection = self.listbox.curselection()
        if selection:
            index = selection[0]
            answer = self.answers[index]
            
            # Update preview
            self.preview_text.config(state=tk.NORMAL)
            self.preview_text.delete(1.0, tk.END)
            self.preview_text.insert(1.0, answer)
            self.preview_text.config(state=tk.DISABLED)
            
            # Enable buttons
            self.edit_btn.config(state=tk.NORMAL)
            self.delete_btn.config(state=tk.NORMAL)
        else:
            # Clear preview and disable buttons
            self.preview_text.config(state=tk.NORMAL)
            self.preview_text.delete(1.0, tk.END)
            self.preview_text.config(state=tk.DISABLED)
            
            self.edit_btn.config(state=tk.DISABLED)
            self.delete_btn.config(state=tk.DISABLED)

class ManualAnswerDialog:
    """Dialog for manually entering/editing answers"""
    
    def __init__(self, parent: tk.Widget, initial_text: str = ""):
        self.parent = parent
        self.result = None
        self.initial_text = initial_text
        
        self.create_dialog()
    
    def create_dialog(self):
        """Create the dialog window"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Enter Answer" if not self.initial_text else "Edit Answer")
        self.dialog.geometry("500x300")
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
        
        # Label
        label = ttk.Label(main_frame, text="Enter the answer text:")
        label.pack(anchor=tk.W, pady=(0, 5))
        
        # Text widget
        self.text_widget = tk.Text(
            main_frame,
            wrap=tk.WORD,
            font=('Arial', 11),
            height=10
        )
        
        # Scrollbar for text widget
        text_scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.text_widget.yview)
        self.text_widget.configure(yscrollcommand=text_scrollbar.set)
        
        # Pack text widget and scrollbar
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Insert initial text
        if self.initial_text:
            self.text_widget.insert(1.0, self.initial_text)
            self.text_widget.focus_set()
            self.text_widget.mark_set(tk.INSERT, tk.END)
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        # Buttons
        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="OK", command=self.ok).pack(side=tk.RIGHT)
        
        # Bind events
        self.dialog.bind('<Return>', lambda e: self.ok())
        self.dialog.bind('<Escape>', lambda e: self.cancel())
        
        # Focus on text widget
        self.text_widget.focus_set()
        
        # Wait for dialog to close
        self.dialog.wait_window()
    
    def ok(self):
        """Handle OK button"""
        text = self.text_widget.get(1.0, tk.END).strip()
        if text:
            self.result = text
        self.dialog.destroy()
    
    def cancel(self):
        """Handle Cancel button"""
        self.result = None
        self.dialog.destroy()

class AutoExtractionDialog:
    """Dialog for auto-extracting answers from document"""
    
    def __init__(self, parent: tk.Widget, document_data: Dict[str, Any], extractor: AnswerExtractor):
        self.parent = parent
        self.document_data = document_data
        self.extractor = extractor
        self.result = None
        self.candidates = []
        self.selected_candidates = []
        
        self.create_dialog()
    
    def create_dialog(self):
        """Create the auto-extraction dialog"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Auto Extract Answers")
        self.dialog.geometry("800x700")
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
        
        # Title
        title_label = ttk.Label(main_frame, text="Auto Extract Answers", font=('Arial', 14, 'bold'))
        title_label.pack(anchor=tk.W, pady=(0, 15))
        
        # Extraction options frame
        options_frame = ttk.LabelFrame(main_frame, text="Extraction Options", padding=10)
        options_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Method selection
        methods_frame = ttk.Frame(options_frame)
        methods_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(methods_frame, text="Extraction Methods:").pack(anchor=tk.W)
        
        methods_inner_frame = ttk.Frame(methods_frame)
        methods_inner_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.method_vars = {
            'sentences': tk.BooleanVar(value=True),
            'paragraphs': tk.BooleanVar(value=True),
            'lists': tk.BooleanVar(value=True),
            'definitions': tk.BooleanVar(value=True),
            'facts': tk.BooleanVar(value=True),
            'procedures': tk.BooleanVar(value=False)
        }
        
        method_labels = {
            'sentences': 'Individual Sentences',
            'paragraphs': 'Paragraphs',
            'lists': 'List Items',
            'definitions': 'Definitions',
            'facts': 'Facts & Statistics',
            'procedures': 'Procedures & Steps'
        }
        
        # Arrange checkboxes in two columns
        left_frame = ttk.Frame(methods_inner_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        right_frame = ttk.Frame(methods_inner_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        
        methods_list = list(self.method_vars.keys())
        for i, method in enumerate(methods_list):
            frame = left_frame if i < 3 else right_frame
            ttk.Checkbutton(
                frame,
                text=method_labels[method],
                variable=self.method_vars[method]
            ).pack(anchor=tk.W, pady=2)
        
        # Filter options
        filter_frame = ttk.Frame(options_frame)
        filter_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(filter_frame, text="Length Filters:").pack(anchor=tk.W)
        
        length_frame = ttk.Frame(filter_frame)
        length_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Label(length_frame, text="Min Length:").pack(side=tk.LEFT)
        self.min_length_var = tk.StringVar(value="20")
        ttk.Entry(length_frame, textvariable=self.min_length_var, width=8).pack(side=tk.LEFT, padx=(5, 15))
        
        ttk.Label(length_frame, text="Max Length:").pack(side=tk.LEFT)
        self.max_length_var = tk.StringVar(value="500")
        ttk.Entry(length_frame, textvariable=self.max_length_var, width=8).pack(side=tk.LEFT, padx=(5, 15))
        
        ttk.Label(length_frame, text="Min Confidence:").pack(side=tk.LEFT)
        self.min_confidence_var = tk.StringVar(value="0.3")
        ttk.Entry(length_frame, textvariable=self.min_confidence_var, width=8).pack(side=tk.LEFT, padx=(5, 0))
        
        # Extract button
        extract_btn = ttk.Button(options_frame, text="Extract Candidates", command=self.extract_candidates)
        extract_btn.pack(pady=(10, 0))
        
        # Results frame
        results_frame = ttk.LabelFrame(main_frame, text="Extraction Results", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Candidates list
        list_frame = ttk.Frame(results_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Treeview for candidates
        columns = ('Method', 'Confidence', 'Length', 'Preview')
        self.candidates_tree = ttk.Treeview(list_frame, columns=columns, show='tree headings', height=12)
        
        self.candidates_tree.heading('#0', text='Select')
        self.candidates_tree.heading('Method', text='Method')
        self.candidates_tree.heading('Confidence', text='Confidence')
        self.candidates_tree.heading('Length', text='Length')
        self.candidates_tree.heading('Preview', text='Preview')
        
        self.candidates_tree.column('#0', width=60)
        self.candidates_tree.column('Method', width=100)
        self.candidates_tree.column('Confidence', width=80)
        self.candidates_tree.column('Length', width=60)
        self.candidates_tree.column('Preview', width=400)
        
        # Scrollbar for treeview
        tree_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.candidates_tree.yview)
        self.candidates_tree.configure(yscrollcommand=tree_scrollbar.set)
        
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.candidates_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Selection controls
        selection_frame = ttk.Frame(results_frame)
        selection_frame.pack(fill=tk.X)
        
        ttk.Button(selection_frame, text="Select All", command=self.select_all).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(selection_frame, text="Select None", command=self.select_none).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(selection_frame, text="Select High Confidence", command=self.select_high_confidence).pack(side=tk.LEFT)
        
        self.selection_label = ttk.Label(selection_frame, text="0 selected")
        self.selection_label.pack(side=tk.RIGHT)
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="Add Selected", command=self.add_selected).pack(side=tk.RIGHT)
        
        # Bind events
        self.candidates_tree.bind('<Button-1>', self.on_tree_click)
        self.dialog.bind('<Escape>', lambda e: self.cancel())
        
        # Initial extraction
        self.extract_candidates()
        
        # Wait for dialog to close
        self.dialog.wait_window()
    
    def extract_candidates(self):
        """Extract answer candidates from document"""
        try:
            # Update extractor settings
            min_length = int(self.min_length_var.get())
            max_length = int(self.max_length_var.get())
            min_confidence = float(self.min_confidence_var.get())
            
            self.extractor.set_filters(min_length, max_length, min_confidence)
            
            # Get selected methods
            selected_methods = [method for method, var in self.method_vars.items() if var.get()]
            
            if not selected_methods:
                messagebox.showwarning("Warning", "Please select at least one extraction method")
                return
            
            # Extract candidates
            content = self.document_data.get('content', '')
            self.candidates = self.extractor.extract_answers(content, selected_methods)
            
            # Update tree
            self.update_candidates_tree()
            
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid filter values: {str(e)}")
        except Exception as e:
            messagebox.showerror("Error", f"Extraction failed: {str(e)}")
    
    def update_candidates_tree(self):
        """Update the candidates tree view"""
        # Clear existing items
        for item in self.candidates_tree.get_children():
            self.candidates_tree.delete(item)
        
        # Add candidates
        for i, candidate in enumerate(self.candidates):
            preview = candidate.text[:100] + "..." if len(candidate.text) > 100 else candidate.text
            preview = preview.replace('\n', ' ').replace('\r', ' ')
            
            item_id = self.candidates_tree.insert('', 'end', 
                text='☐',  # Unchecked checkbox
                values=(
                    candidate.extraction_method,
                    f"{candidate.confidence:.2f}",
                    str(len(candidate.text)),
                    preview
                ),
                tags=('candidate',)
            )
        
        self.update_selection_count()
    
    def on_tree_click(self, event):
        """Handle tree click for checkbox functionality"""
        item = self.candidates_tree.identify_row(event.y)
        if item:
            # Toggle selection
            current_text = self.candidates_tree.item(item, 'text')
            if current_text == '☐':
                self.candidates_tree.item(item, text='☑')
            else:
                self.candidates_tree.item(item, text='☐')
            
            self.update_selection_count()
    
    def select_all(self):
        """Select all candidates"""
        for item in self.candidates_tree.get_children():
            self.candidates_tree.item(item, text='☑')
        self.update_selection_count()
    
    def select_none(self):
        """Deselect all candidates"""
        for item in self.candidates_tree.get_children():
            self.candidates_tree.item(item, text='☐')
        self.update_selection_count()
    
    def select_high_confidence(self):
        """Select only high confidence candidates (>0.7)"""
        for i, item in enumerate(self.candidates_tree.get_children()):
            if i < len(self.candidates):
                if self.candidates[i].confidence > 0.7:
                    self.candidates_tree.item(item, text='☑')
                else:
                    self.candidates_tree.item(item, text='☐')
        self.update_selection_count()
    
    def update_selection_count(self):
        """Update the selection count label"""
        selected_count = sum(1 for item in self.candidates_tree.get_children() 
                           if self.candidates_tree.item(item, 'text') == '☑')
        self.selection_label.config(text=f"{selected_count} selected")
    
    def add_selected(self):
        """Add selected candidates to answers"""
        selected_candidates = []
        
        for i, item in enumerate(self.candidates_tree.get_children()):
            if self.candidates_tree.item(item, 'text') == '☑' and i < len(self.candidates):
                selected_candidates.append(self.candidates[i])
        
        if not selected_candidates:
            messagebox.showwarning("Warning", "No candidates selected")
            return
        
        self.result = selected_candidates
        self.dialog.destroy()
    
    def cancel(self):
        """Cancel the extraction"""
        self.result = None
        self.dialog.destroy()