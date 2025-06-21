"""
Optimized document viewer with pagination for large documents
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any, Callable, Optional, List
import threading
import math

from core.optimized_document_parser import OptimizedDocumentParser

class OptimizedDocumentViewer:
    """Document viewer optimized for large files with pagination"""
    
    def __init__(self, parent: tk.Widget, selection_callback: Callable[[str, int, int], None]):
        self.parent = parent
        self.selection_callback = selection_callback
        self.current_document = None
        self.doc_parser = OptimizedDocumentParser()
        
        # Pagination settings
        self.current_page = 0
        self.chars_per_page = 20000  # Characters to show per page
        self.total_pages = 0
        self.page_content_cache = {}  # Cache for loaded pages
        self.max_cache_size = 10  # Maximum pages to keep in cache
        
        # Loading state
        self.is_loading = False
        self.load_thread = None
        
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the optimized document viewer UI"""
        # Main frame
        self.frame = ttk.Frame(self.parent)
        self.frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Title and controls frame
        self.header_frame = ttk.Frame(self.frame)
        self.header_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Title label
        self.title_label = ttk.Label(self.header_frame, text="Document Viewer", font=('Arial', 12, 'bold'))
        self.title_label.pack(side=tk.LEFT)
        
        # Pagination controls
        self.pagination_frame = ttk.Frame(self.header_frame)
        self.pagination_frame.pack(side=tk.RIGHT)
        
        self.prev_btn = ttk.Button(
            self.pagination_frame,
            text="◀ Prev",
            command=self.prev_page,
            state=tk.DISABLED,
            width=8
        )
        self.prev_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.page_label = ttk.Label(self.pagination_frame, text="Page 0 / 0")
        self.page_label.pack(side=tk.LEFT, padx=(0, 5))
        
        self.next_btn = ttk.Button(
            self.pagination_frame,
            text="Next ▶",
            command=self.next_page,
            state=tk.DISABLED,
            width=8
        )
        self.next_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Jump to page
        self.goto_frame = ttk.Frame(self.pagination_frame)
        self.goto_frame.pack(side=tk.LEFT, padx=(10, 0))
        
        ttk.Label(self.goto_frame, text="Go to:").pack(side=tk.LEFT)
        
        self.goto_var = tk.StringVar()
        self.goto_entry = ttk.Entry(self.goto_frame, textvariable=self.goto_var, width=5)
        self.goto_entry.pack(side=tk.LEFT, padx=(2, 2))
        self.goto_entry.bind('<Return>', self.goto_page)
        
        ttk.Button(self.goto_frame, text="Go", command=self.goto_page, width=3).pack(side=tk.LEFT)
        
        # Info frame
        self.info_frame = ttk.Frame(self.frame)
        self.info_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.info_label = ttk.Label(self.info_frame, text="No document loaded")
        self.info_label.pack(side=tk.LEFT)
        
        # Loading indicator
        self.loading_label = ttk.Label(self.info_frame, text="", foreground="blue")
        self.loading_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Selection info
        self.selection_label = ttk.Label(self.info_frame, text="", foreground="blue")
        self.selection_label.pack(side=tk.RIGHT)
        
        # Text widget with scrollbar
        self.text_frame = ttk.Frame(self.frame)
        self.text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.text_widget = tk.Text(
            self.text_frame,
            wrap=tk.WORD,
            font=('Arial', 11),
            selectbackground='lightblue',
            selectforeground='black',
            state=tk.DISABLED
        )
        
        # Scrollbar
        self.scrollbar = ttk.Scrollbar(self.text_frame, orient=tk.VERTICAL, command=self.text_widget.yview)
        self.text_widget.configure(yscrollcommand=self.scrollbar.set)
        
        # Pack text widget and scrollbar
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Control frame
        self.control_frame = ttk.Frame(self.frame)
        self.control_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.add_selection_btn = ttk.Button(
            self.control_frame,
            text="Add Selected Text as Answer",
            command=self.add_selected_text,
            state=tk.DISABLED
        )
        self.add_selection_btn.pack(side=tk.LEFT)
        
        # Page size controls
        self.page_size_frame = ttk.Frame(self.control_frame)
        self.page_size_frame.pack(side=tk.RIGHT)
        
        ttk.Label(self.page_size_frame, text="Page size:").pack(side=tk.LEFT)
        
        self.page_size_var = tk.StringVar(value="20000")
        page_size_combo = ttk.Combobox(
            self.page_size_frame,
            textvariable=self.page_size_var,
            values=["10000", "20000", "50000", "100000"],
            width=8,
            state="readonly"
        )
        page_size_combo.pack(side=tk.LEFT, padx=(5, 0))
        page_size_combo.bind('<<ComboboxSelected>>', self.change_page_size)
        
        # Bind events
        self.text_widget.bind('<<Selection>>', self.on_text_selection)
        self.text_widget.bind('<Button-1>', self.on_click)
        self.text_widget.bind('<ButtonRelease-1>', self.on_release)
        self.text_widget.bind('<Button-3>', self.on_right_click)  # Right click to add answer
    
    def load_document(self, document_data: Dict[str, Any]):
        """Load document into the viewer"""
        self.current_document = document_data
        self.current_page = 0
        self.page_content_cache.clear()
        
        metadata = document_data.get('metadata', {})
        total_chars = metadata.get('total_characters', 0)
        
        # Calculate total pages
        self.chars_per_page = int(self.page_size_var.get())
        self.total_pages = max(1, math.ceil(total_chars / self.chars_per_page))
        
        # Update info label
        file_name = metadata.get('file_path', 'Unknown')
        file_type = metadata.get('file_type', 'unknown')
        
        if metadata.get('is_lazy', False):
            chunk_count = metadata.get('chunk_count', 0)
            info_text = f"{file_name} ({file_type.upper()}, {total_chars:,} chars, {chunk_count} chunks, paginated)"
        else:
            info_text = f"{file_name} ({file_type.upper()}, {total_chars:,} chars)"
        
        self.info_label.config(text=info_text)
        
        # Update pagination controls
        self.update_pagination_controls()
        
        # Load first page
        self.load_page(0)
    
    def load_page(self, page_num: int):
        """Load a specific page"""
        if not self.current_document or page_num < 0 or page_num >= self.total_pages:
            return
        
        # Check cache first
        if page_num in self.page_content_cache:
            self.display_page_content(page_num, self.page_content_cache[page_num])
            return
        
        # Load page content
        self.is_loading = True
        self.loading_label.config(text="Loading page...")
        self.update_pagination_controls()
        
        # Load in thread for large documents
        if self.current_document.get('lazy_content', False):
            self.load_thread = threading.Thread(
                target=self._load_page_threaded,
                args=(page_num,),
                daemon=True
            )
            self.load_thread.start()
        else:
            # Load immediately for small documents
            content = self._get_page_content(page_num)
            self.display_page_content(page_num, content)
    
    def _load_page_threaded(self, page_num: int):
        """Load page content in a separate thread"""
        try:
            content = self._get_page_content(page_num)
            
            # Update UI in main thread
            self.parent.after(0, self.display_page_content, page_num, content)
        
        except Exception as e:
            error_msg = f"Error loading page: {str(e)}"
            self.parent.after(0, self.display_page_content, page_num, error_msg)
    
    def _get_page_content(self, page_num: int) -> str:
        """Get content for a specific page"""
        start_char = page_num * self.chars_per_page
        end_char = min(start_char + self.chars_per_page, 
                      self.current_document.get('metadata', {}).get('total_characters', 0))
        
        if self.current_document.get('lazy_content', False):
            # Use optimized parser for lazy-loaded documents
            return self.doc_parser.get_text_at_position(
                self.current_document, start_char, end_char
            )
        else:
            # Regular content access
            content = self.current_document.get('content', '')
            return content[start_char:end_char]
    
    def display_page_content(self, page_num: int, content: str):
        """Display page content in the text widget"""
        self.current_page = page_num
        
        # Cache the content
        self.page_content_cache[page_num] = content
        
        # Limit cache size
        if len(self.page_content_cache) > self.max_cache_size:
            # Remove oldest entries
            oldest_keys = sorted(self.page_content_cache.keys())
            for key in oldest_keys[:-self.max_cache_size]:
                del self.page_content_cache[key]
        
        # Update text widget
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.delete(1.0, tk.END)
        self.text_widget.insert(1.0, content)
        self.text_widget.config(state=tk.DISABLED)
        
        # Update pagination
        self.is_loading = False
        self.loading_label.config(text="")
        self.update_pagination_controls()
        
        # Reset selection
        self.selection_label.config(text="")
        self.add_selection_btn.config(state=tk.DISABLED)
    
    def update_pagination_controls(self):
        """Update pagination control states"""
        if self.is_loading:
            self.prev_btn.config(state=tk.DISABLED)
            self.next_btn.config(state=tk.DISABLED)
            return
        
        # Update page label
        self.page_label.config(text=f"Page {self.current_page + 1} / {self.total_pages}")
        
        # Update button states
        self.prev_btn.config(state=tk.NORMAL if self.current_page > 0 else tk.DISABLED)
        self.next_btn.config(state=tk.NORMAL if self.current_page < self.total_pages - 1 else tk.DISABLED)
    
    def prev_page(self):
        """Go to previous page"""
        if self.current_page > 0:
            self.load_page(self.current_page - 1)
    
    def next_page(self):
        """Go to next page"""
        if self.current_page < self.total_pages - 1:
            self.load_page(self.current_page + 1)
    
    def goto_page(self, event=None):
        """Go to specified page"""
        try:
            page_num = int(self.goto_var.get()) - 1  # Convert to 0-based
            if 0 <= page_num < self.total_pages:
                self.load_page(page_num)
                self.goto_var.set("")
            else:
                messagebox.showwarning("Invalid Page", f"Page must be between 1 and {self.total_pages}")
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid page number")
    
    def change_page_size(self, event=None):
        """Change the page size and reload"""
        if not self.current_document:
            return
        
        old_char_pos = self.current_page * self.chars_per_page
        self.chars_per_page = int(self.page_size_var.get())
        
        # Recalculate total pages
        total_chars = self.current_document.get('metadata', {}).get('total_characters', 0)
        self.total_pages = max(1, math.ceil(total_chars / self.chars_per_page))
        
        # Calculate new page to maintain position
        new_page = min(old_char_pos // self.chars_per_page, self.total_pages - 1)
        
        # Clear cache and reload
        self.page_content_cache.clear()
        self.load_page(new_page)
    
    def on_text_selection(self, event=None):
        """Handle text selection event"""
        try:
            selected_text = self.text_widget.selection_get()
            if selected_text:
                # Get selection indices relative to current page
                start_idx = self.text_widget.index(tk.SEL_FIRST)
                end_idx = self.text_widget.index(tk.SEL_LAST)
                
                # Convert to global character positions
                page_start_char = self.current_page * self.chars_per_page
                start_pos = page_start_char + self.get_char_position(start_idx)
                end_pos = page_start_char + self.get_char_position(end_idx)
                
                # Update selection info
                char_count = len(selected_text)
                self.selection_label.config(text=f"Selected: {char_count} characters")
                self.add_selection_btn.config(state=tk.NORMAL)
                
                return selected_text, start_pos, end_pos
            else:
                self.selection_label.config(text="")
                self.add_selection_btn.config(state=tk.DISABLED)
                
        except tk.TclError:
            self.selection_label.config(text="")
            self.add_selection_btn.config(state=tk.DISABLED)
        
        return None, 0, 0
    
    def get_char_position(self, text_index: str) -> int:
        """Convert text widget index to character position within current page"""
        try:
            text_up_to_index = self.text_widget.get(1.0, text_index)
            return len(text_up_to_index)
        except:
            return 0
    
    def on_click(self, event=None):
        """Handle mouse click"""
        self.selection_label.config(text="")
        self.add_selection_btn.config(state=tk.DISABLED)
    
    def on_release(self, event=None):
        """Handle mouse release - check for selection"""
        self.text_widget.after_idle(self.on_text_selection)
    
    def add_selected_text(self):
        """Add selected text as an answer"""
        try:
            selected_text = self.text_widget.selection_get()
            if selected_text.strip():
                # Get global positions
                start_idx = self.text_widget.index(tk.SEL_FIRST)
                end_idx = self.text_widget.index(tk.SEL_LAST)
                
                page_start_char = self.current_page * self.chars_per_page
                start_pos = page_start_char + self.get_char_position(start_idx)
                end_pos = page_start_char + self.get_char_position(end_idx)
                
                # Call the callback
                self.selection_callback(selected_text, start_pos, end_pos)
                
                # Clear selection
                self.text_widget.selection_clear()
                self.selection_label.config(text="")
                self.add_selection_btn.config(state=tk.DISABLED)
                
        except tk.TclError:
            pass
    
    def search_in_document(self, search_term: str) -> List[Dict[str, Any]]:
        """Search for term in document"""
        if not self.current_document:
            return []
        
        if self.current_document.get('lazy_content', False):
            return self.doc_parser.search_in_document(self.current_document, search_term)
        else:
            # Regular search for small documents
            content = self.current_document.get('content', '')
            results = []
            start = 0
            while True:
                pos = content.find(search_term, start)
                if pos == -1:
                    break
                results.append({
                    'position': pos,
                    'context': content[max(0, pos-50):pos+len(search_term)+50],
                    'page': pos // self.chars_per_page
                })
                start = pos + 1
            return results
    
    def jump_to_position(self, char_position: int):
        """Jump to a specific character position in the document"""
        target_page = char_position // self.chars_per_page
        target_page = min(target_page, self.total_pages - 1)
        
        if target_page != self.current_page:
            self.load_page(target_page)
        
        # Highlight the position within the page
        page_start = target_page * self.chars_per_page
        relative_pos = char_position - page_start
        
        # Convert to text widget position (rough approximation)
        self.text_widget.after(100, self._highlight_position, relative_pos)
    
    def _highlight_position(self, relative_pos: int):
        """Highlight a position within the current page"""
        try:
            # This is a simplified approach - in practice, you'd need more
            # sophisticated position mapping
            content = self.text_widget.get(1.0, tk.END)
            if relative_pos < len(content):
                # Convert character position to line.column format
                lines = content[:relative_pos].split('\n')
                line_num = len(lines)
                char_in_line = len(lines[-1]) if lines else 0
                
                index = f"{line_num}.{char_in_line}"
                self.text_widget.mark_set(tk.INSERT, index)
                self.text_widget.see(index)
                
                # Briefly highlight the area
                end_index = f"{line_num}.{char_in_line + 50}"
                self.text_widget.tag_add("highlight", index, end_index)
                self.text_widget.tag_config("highlight", background="yellow")
                self.text_widget.after(2000, lambda: self.text_widget.tag_delete("highlight"))
        except:
            pass
    
    def on_right_click(self, event):
        """Handle right click to directly add selected text as answer"""
        try:
            selected_text = self.text_widget.selection_get()
            if selected_text.strip():
                self.add_selected_text()
        except tk.TclError:
            # No selection, do nothing
            pass
    
