"""
Optimized auto-extraction dialog for large documents with progress and virtual scrolling
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any, List, Optional
import threading
import time
import sys,os

from core.answer_extractor import AnswerExtractor, AnswerCandidate, ExtractionProgress

class AutoExtractionDialog:
    """Optimized auto-extraction dialog for large documents"""
    
    def __init__(self, parent: tk.Widget, document_data: Dict[str, Any]):
        self.parent = parent
        self.document_data = document_data
        self.result = None
        self.candidates = []
        self.displayed_candidates = []  # Subset currently displayed
        self.selected_indices = set()
        
        # Optimized extractor
        self.extractor = AnswerExtractor()
        
        # Virtual scrolling settings
        self.items_per_page = 100
        self.current_page = 0
        self.total_pages = 0
        
        # Extraction state
        self.extraction_thread = None
        self.is_extracting = False
        
        self.create_dialog()
    
    def create_dialog(self):
        """Create the optimized auto-extraction dialog"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Auto Extract Answers (Optimized)")
        self.dialog.geometry("900x700")
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
        
        # Title and document info
        title_label = ttk.Label(main_frame, text="Auto Extract Answers", font=('Arial', 12, 'bold'))
        title_label.pack(anchor=tk.W, pady=(0, 5))
        
        # Document info
        self.create_document_info(main_frame)
        
        # Extraction options
        self.create_extraction_options(main_frame)
        
        # Results section with virtual scrolling
        self.create_results_section(main_frame)
        
        # Progress section (compact, shown only during extraction)
        self.create_progress_section(main_frame)
        
        # Button frame - always at bottom
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
        
        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="Add Selected", command=self.add_selected).pack(side=tk.RIGHT)
        
        # Bind events
        self.dialog.bind('<Escape>', lambda e: self.cancel())
        self.dialog.protocol("WM_DELETE_WINDOW", self.cancel)
        
        # Remove the extraction estimate popup
        
        # Wait for dialog to close
        self.dialog.wait_window()
    
    def create_document_info(self, parent):
        """Create document information section"""
        info_frame = ttk.LabelFrame(parent, text="Document Information", padding=5)
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        metadata = self.document_data.get('metadata', {})
        file_name = os.path.basename(metadata.get('file_path', 'Unknown'))
        chars = metadata.get('total_characters', 0)
        
        info_text = f"{file_name} • {chars:,} characters"
        if metadata.get('is_lazy', False):
            info_text += f" • {metadata.get('chunk_count', 0)} chunks (optimized mode)"
        
        ttk.Label(info_frame, text=info_text).pack(anchor=tk.W)
    
    def create_extraction_options(self, parent):
        """Create extraction options section"""
        options_frame = ttk.LabelFrame(parent, text="Extraction Options", padding=5)
        options_frame.pack(fill=tk.X, pady=(0, 10))
        
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
        
        ttk.Label(filter_frame, text="Filters:").pack(anchor=tk.W)
        
        filter_inner_frame = ttk.Frame(filter_frame)
        filter_inner_frame.pack(fill=tk.X, pady=(5, 0))
        
        # First row
        filter_row1 = ttk.Frame(filter_inner_frame)
        filter_row1.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(filter_row1, text="Min Length:").pack(side=tk.LEFT)
        self.min_length_var = tk.StringVar(value="20")
        ttk.Entry(filter_row1, textvariable=self.min_length_var, width=8).pack(side=tk.LEFT, padx=(5, 15))        
        ttk.Label(filter_row1, text="Max Length:").pack(side=tk.LEFT)
        self.max_length_var = tk.StringVar(value="500")
        ttk.Entry(filter_row1, textvariable=self.max_length_var, width=8).pack(side=tk.LEFT, padx=(5, 15))
        
        ttk.Label(filter_row1, text="Min Confidence:").pack(side=tk.LEFT)
        self.min_confidence_var = tk.StringVar(value="0.3")
        ttk.Entry(filter_row1, textvariable=self.min_confidence_var, width=8).pack(side=tk.LEFT, padx=(5, 0))
        
        # Second row
        filter_row2 = ttk.Frame(filter_inner_frame)
        filter_row2.pack(fill=tk.X)
        
        ttk.Label(filter_row2, text="Max Candidates:").pack(side=tk.LEFT)
        self.max_candidates_var = tk.StringVar(value="5000")
        ttk.Entry(filter_row2, textvariable=self.max_candidates_var, width=8).pack(side=tk.LEFT, padx=(5, 0))
        
        # Extract button
        extract_btn = ttk.Button(options_frame, text="Start Extraction", command=self.start_extraction)
        extract_btn.pack(pady=(5, 0))
    
    def create_progress_section(self, parent):
        """Create progress tracking section"""
        self.progress_frame = ttk.LabelFrame(parent, text="Progress", padding=5)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            self.progress_frame,
            variable=self.progress_var,
            maximum=100,
            length=300
        )
        self.progress_bar.pack(side=tk.LEFT, padx=(0, 10))
        
        # Progress label
        self.progress_label = ttk.Label(self.progress_frame, text="Ready to extract")
        self.progress_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Stop button
        self.stop_btn = ttk.Button(
            self.progress_frame,
            text="Stop",
            command=self.stop_extraction,
            state=tk.DISABLED,
            width=8
        )
        self.stop_btn.pack(side=tk.RIGHT)
        
        # Initially hide progress section
        self.progress_frame.pack_forget()
    
    def create_results_section(self, parent):
        """Create results section with virtual scrolling"""
        results_frame = ttk.LabelFrame(parent, text="Extraction Results", padding=5)
        results_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        # Virtual scrolling controls
        scroll_controls = ttk.Frame(results_frame)
        scroll_controls.pack(fill=tk.X, pady=(0, 10))
        
        # Pagination for results
        self.results_pagination = ttk.Frame(scroll_controls)
        self.results_pagination.pack(side=tk.LEFT)
        
        self.prev_results_btn = ttk.Button(
            self.results_pagination,
            text="◀ Prev",
            command=self.prev_results_page,
            state=tk.DISABLED,
            width=8
        )
        self.prev_results_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.results_page_label = ttk.Label(self.results_pagination, text="Page 0 / 0")
        self.results_page_label.pack(side=tk.LEFT, padx=(0, 5))
        
        self.next_results_btn = ttk.Button(
            self.results_pagination,
            text="Next ▶",
            command=self.next_results_page,
            state=tk.DISABLED,
            width=8
        )
        self.next_results_btn.pack(side=tk.LEFT)
        
        # Selection controls
        selection_controls = ttk.Frame(scroll_controls)
        selection_controls.pack(side=tk.RIGHT)
        
        ttk.Button(selection_controls, text="Select All", command=self.select_all).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(selection_controls, text="Select Page", command=self.select_page).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(selection_controls, text="Select None", command=self.select_none).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(selection_controls, text="High Confidence", command=self.select_high_confidence).pack(side=tk.LEFT)
        
        self.selection_count_label = ttk.Label(selection_controls, text="0 selected")
        self.selection_count_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Results list
        list_frame = ttk.Frame(results_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
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
        self.candidates_tree.column('Preview', width=500)
        
        # Scrollbar for treeview
        tree_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.candidates_tree.yview)
        self.candidates_tree.configure(yscrollcommand=tree_scrollbar.set)
        
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.candidates_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Bind events
        self.candidates_tree.bind('<Button-1>', self.on_tree_click)
        self.candidates_tree.bind('<Double-Button-1>', self.on_tree_double_click)
    
    
    def start_extraction(self):
        """Start the extraction process"""
        try:
            # Update extractor settings
            min_length = int(self.min_length_var.get())
            max_length = int(self.max_length_var.get())
            min_confidence = float(self.min_confidence_var.get())
            max_candidates = int(self.max_candidates_var.get())
            
            self.extractor.update_extraction_settings(
                min_length=min_length,
                max_length=max_length,
                min_confidence=min_confidence
            )
            
            # Get selected methods
            selected_methods = [method for method, var in self.method_vars.items() if var.get()]
            
            if not selected_methods:
                messagebox.showwarning("Warning", "Please select at least one extraction method")
                return
            
            # Show progress section before button frame
            button_frame = None
            for child in self.progress_frame.master.winfo_children():
                if isinstance(child, ttk.Frame) and len(child.winfo_children()) == 2:  # Button frame
                    button_frame = child
                    break
            
            if button_frame:
                self.progress_frame.pack(fill=tk.X, pady=(5, 5), before=button_frame)
            else:
                self.progress_frame.pack(fill=tk.X, pady=(5, 5))
            
            # Start extraction
            self.is_extracting = True
            self.stop_btn.config(state=tk.NORMAL)
            self.candidates = []
            self.selected_indices.clear()
            
            # Start threaded extraction
            self.extraction_thread = self.extractor.extract_answers_threaded(
                self.document_data,
                methods=selected_methods,
                progress_callback=self.on_extraction_progress,
                completion_callback=self.on_extraction_complete,
                error_callback=self.on_extraction_error,
                max_candidates=max_candidates
            )
            
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid settings: {str(e)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start extraction: {str(e)}")
    
    def on_extraction_progress(self, progress: ExtractionProgress):
        """Handle extraction progress updates"""
        if progress.error_message:
            self.on_extraction_error(progress.error_message)
            return
        
        # Update progress bar
        if progress.total_chunks > 0:
            progress_percent = (progress.current_chunk / progress.total_chunks) * 100
            self.progress_var.set(progress_percent)
        
        # Update label
        self.progress_label.config(
            text=f"Chunk {progress.current_chunk}/{progress.total_chunks} - {progress.current_method} ({progress.candidates_found} found)"
        )
        
        if progress.is_complete:
            self.is_extracting = False
            self.stop_btn.config(state=tk.DISABLED)
    
    def on_extraction_complete(self, candidates: List[AnswerCandidate]):
        """Handle extraction completion"""
        self.candidates = candidates
        self.update_results_display()
        
        self.progress_label.config(text=f"Complete - {len(candidates)} candidates found")
        self.is_extracting = False
        self.stop_btn.config(state=tk.DISABLED)
    
    def on_extraction_error(self, error_message: str):
        """Handle extraction error"""
        messagebox.showerror("Extraction Error", f"Extraction failed: {error_message}")
        self.is_extracting = False
        self.stop_btn.config(state=tk.DISABLED)
        self.progress_label.config(text="Extraction failed")
    
    def stop_extraction(self):
        """Stop the current extraction"""
        self.extractor.stop_current_extraction()
        self.is_extracting = False
        self.stop_btn.config(state=tk.DISABLED)
        self.progress_label.config(text="Extraction stopped")
    
    def update_results_display(self):
        """Update the results display with virtual scrolling"""
        if not self.candidates:
            return
        
        # Calculate pagination
        total_candidates = len(self.candidates)
        self.total_pages = max(1, (total_candidates + self.items_per_page - 1) // self.items_per_page)
        self.current_page = min(self.current_page, self.total_pages - 1)
        
        # Get candidates for current page
        start_idx = self.current_page * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, total_candidates)
        self.displayed_candidates = self.candidates[start_idx:end_idx]
        
        # Update tree
        self.update_candidates_tree()
        
        # Update pagination controls
        self.update_results_pagination()
    
    def update_candidates_tree(self):
        """Update the candidates tree view"""
        # Clear existing items
        for item in self.candidates_tree.get_children():
            self.candidates_tree.delete(item)
        
        # Add candidates for current page
        start_idx = self.current_page * self.items_per_page
        
        for i, candidate in enumerate(self.displayed_candidates):
            global_idx = start_idx + i
            preview = candidate.text[:150] + "..." if len(candidate.text) > 150 else candidate.text
            preview = preview.replace('\n', ' ').replace('\r', ' ')
            
            # Check if this candidate is selected
            checkbox = '☑' if global_idx in self.selected_indices else '☐'
            
            item_id = self.candidates_tree.insert('', 'end',
                text=checkbox,
                values=(
                    candidate.extraction_method,
                    f"{candidate.confidence:.2f}",
                    str(len(candidate.text)),
                    preview
                ),
                tags=('candidate',)
            )
        
        self.update_selection_count()
    
    def update_results_pagination(self):
        """Update results pagination controls"""
        self.results_page_label.config(text=f"Page {self.current_page + 1} / {self.total_pages}")
        
        self.prev_results_btn.config(state=tk.NORMAL if self.current_page > 0 else tk.DISABLED)
        self.next_results_btn.config(state=tk.NORMAL if self.current_page < self.total_pages - 1 else tk.DISABLED)
    
    def prev_results_page(self):
        """Go to previous results page"""
        if self.current_page > 0:
            self.current_page -= 1
            self.update_results_display()
    
    def next_results_page(self):
        """Go to next results page"""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_results_display()
    
    def on_tree_click(self, event):
        """Handle tree click for checkbox functionality"""
        item = self.candidates_tree.identify_row(event.y)
        if item:
            # Get the index of the clicked item
            tree_children = self.candidates_tree.get_children()
            item_index = tree_children.index(item)
            global_index = self.current_page * self.items_per_page + item_index
            
            # Toggle selection
            if global_index in self.selected_indices:
                self.selected_indices.remove(global_index)
                self.candidates_tree.item(item, text='☐')
            else:
                self.selected_indices.add(global_index)
                self.candidates_tree.item(item, text='☑')
            
            self.update_selection_count()
    
    def on_tree_double_click(self, event):
        """Handle tree double-click to show full text"""
        item = self.candidates_tree.identify_row(event.y)
        if item:
            tree_children = self.candidates_tree.get_children()
            item_index = tree_children.index(item)
            
            if item_index < len(self.displayed_candidates):
                candidate = self.displayed_candidates[item_index]
                self.show_candidate_details(candidate)
    
    def show_candidate_details(self, candidate: AnswerCandidate):
        """Show full details of a candidate"""
        detail_window = tk.Toplevel(self.dialog)
        detail_window.title("Candidate Details")
        detail_window.geometry("600x400")
        detail_window.transient(self.dialog)
        
        frame = ttk.Frame(detail_window, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Info
        info_text = f"Method: {candidate.extraction_method}\n"
        info_text += f"Confidence: {candidate.confidence:.2f}\n"
        info_text += f"Length: {len(candidate.text)} characters\n"
        info_text += f"Position: {candidate.start_pos}-{candidate.end_pos}\n\n"
        
        ttk.Label(frame, text=info_text, font=('Arial', 10)).pack(anchor=tk.W)
        
        # Full text
        text_widget = tk.Text(frame, wrap=tk.WORD, font=('Arial', 11))
        text_widget.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        text_widget.insert(1.0, candidate.text)
        text_widget.config(state=tk.DISABLED)
        
        ttk.Button(frame, text="Close", command=detail_window.destroy).pack(pady=(10, 0))
    
    def select_all(self):
        """Select all candidates (across all pages)"""
        total_candidates = len(self.candidates)
        
        # Warn if selecting a large number of candidates
        if total_candidates > 1000:
            if not messagebox.askyesno(
                "Confirm Select All", 
                f"This will select all {total_candidates:,} candidates across all pages.\n\nContinue?"
            ):
                return
        
        for i in range(total_candidates):
            self.selected_indices.add(i)
        self.update_candidates_tree()
    
    def select_page(self):
        """Select all candidates on current page"""
        start_idx = self.current_page * self.items_per_page
        for i in range(len(self.displayed_candidates)):
            self.selected_indices.add(start_idx + i)
        self.update_candidates_tree()
    
    def select_none(self):
        """Deselect all candidates"""
        self.selected_indices.clear()
        self.update_candidates_tree()
    
    def select_high_confidence(self):
        """Select only high confidence candidates"""
        self.selected_indices.clear()
        for i, candidate in enumerate(self.candidates):
            if candidate.confidence > 0.7:
                self.selected_indices.add(i)
        self.update_candidates_tree()
    
    def update_selection_count(self):
        """Update the selection count label"""
        self.selection_count_label.config(text=f"{len(self.selected_indices)} selected")
    
    def add_selected(self):
        """Add selected candidates to answers"""
        if not self.selected_indices:
            messagebox.showwarning("Warning", "No candidates selected")
            return
        
        selected_candidates = [self.candidates[i] for i in sorted(self.selected_indices) if i < len(self.candidates)]
        
        self.result = selected_candidates
        self.dialog.destroy()
    
    def cancel(self):
        """Cancel the extraction"""
        if self.is_extracting:
            self.stop_extraction()
        
        self.result = None
        self.dialog.destroy()