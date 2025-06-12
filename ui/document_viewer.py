"""
Document viewer widget with text selection capabilities
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
from typing import Dict, Any, Callable, Optional

class DocumentViewer:
    """Widget for displaying documents and handling text selection"""
    
    def __init__(self, parent: tk.Widget, selection_callback: Callable[[str, int, int], None]):
        self.parent = parent
        self.selection_callback = selection_callback
        self.current_document = None
        
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the document viewer UI"""
        # Main frame
        self.frame = ttk.Frame(self.parent)
        self.frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Title label
        self.title_label = ttk.Label(self.frame, text="Document Viewer", font=('Arial', 12, 'bold'))
        self.title_label.pack(anchor=tk.W, pady=(0, 5))
        
        # Info frame
        self.info_frame = ttk.Frame(self.frame)
        self.info_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.info_label = ttk.Label(self.info_frame, text="No document loaded")
        self.info_label.pack(side=tk.LEFT)
        
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
        
        # Bind events
        self.text_widget.bind('<<Selection>>', self.on_text_selection)
        self.text_widget.bind('<Button-1>', self.on_click)
        self.text_widget.bind('<ButtonRelease-1>', self.on_release)
    
    def load_document(self, document_data: Dict[str, Any]):
        """Load document content into the viewer"""
        self.current_document = document_data
        content = document_data.get('content', '')
        metadata = document_data.get('metadata', {})
        
        # Enable text widget for editing
        self.text_widget.config(state=tk.NORMAL)
        
        # Clear existing content
        self.text_widget.delete(1.0, tk.END)
        
        # Insert new content
        self.text_widget.insert(1.0, content)
        
        # Disable editing but allow selection
        self.text_widget.config(state=tk.DISABLED)
        
        # Update info label
        file_name = metadata.get('file_path', 'Unknown')
        file_type = metadata.get('file_type', 'unknown')
        total_chars = metadata.get('total_characters', 0)
        
        if file_type == 'pdf':
            total_pages = metadata.get('total_pages', 0)
            info_text = f"{file_name} ({file_type.upper()}, {total_pages} pages, {total_chars:,} characters)"
        else:
            info_text = f"{file_name} ({file_type.upper()}, {total_chars:,} characters)"
        
        self.info_label.config(text=info_text)
        
        # Reset selection
        self.selection_label.config(text="")
        self.add_selection_btn.config(state=tk.DISABLED)
    
    def on_text_selection(self, event=None):
        """Handle text selection event"""
        try:
            # Get selected text
            selected_text = self.text_widget.selection_get()
            if selected_text:
                # Get selection indices
                start_idx = self.text_widget.index(tk.SEL_FIRST)
                end_idx = self.text_widget.index(tk.SEL_LAST)
                
                # Convert to character positions
                start_pos = self.get_char_position(start_idx)
                end_pos = self.get_char_position(end_idx)
                
                # Update selection info
                char_count = len(selected_text)
                self.selection_label.config(text=f"Selected: {char_count} characters")
                self.add_selection_btn.config(state=tk.NORMAL)
                
                return selected_text, start_pos, end_pos
            else:
                self.selection_label.config(text="")
                self.add_selection_btn.config(state=tk.DISABLED)
                
        except tk.TclError:
            # No selection
            self.selection_label.config(text="")
            self.add_selection_btn.config(state=tk.DISABLED)
        
        return None, 0, 0
    
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
                # Get selection positions
                start_idx = self.text_widget.index(tk.SEL_FIRST)
                end_idx = self.text_widget.index(tk.SEL_LAST)
                start_pos = self.get_char_position(start_idx)
                end_pos = self.get_char_position(end_idx)
                
                # Call the callback
                self.selection_callback(selected_text, start_pos, end_pos)
                
                # Clear selection
                self.text_widget.selection_clear()
                self.selection_label.config(text="")
                self.add_selection_btn.config(state=tk.DISABLED)
                
        except tk.TclError:
            pass
    
    def get_char_position(self, text_index: str) -> int:
        """Convert text widget index to character position"""
        try:
            # Get all text up to the index
            text_up_to_index = self.text_widget.get(1.0, text_index)
            return len(text_up_to_index)
        except:
            return 0
    
    def highlight_text(self, start_pos: int, end_pos: int, tag_name: str = "highlight"):
        """Highlight text at specific positions"""
        try:
            # Convert character positions to text widget indices
            start_idx = self.char_position_to_index(start_pos)
            end_idx = self.char_position_to_index(end_pos)
            
            # Add tag
            self.text_widget.tag_add(tag_name, start_idx, end_idx)
            self.text_widget.tag_config(tag_name, background="yellow", foreground="black")
            
        except Exception as e:
            print(f"Error highlighting text: {e}")
    
    def char_position_to_index(self, char_pos: int) -> str:
        """Convert character position to text widget index"""
        try:
            content = self.text_widget.get(1.0, tk.END)
            if char_pos >= len(content):
                return tk.END
            
            # Count lines and characters
            lines = content[:char_pos].split('\n')
            line_num = len(lines)
            char_in_line = len(lines[-1])
            
            return f"{line_num}.{char_in_line}"
        except:
            return "1.0"
    
    def clear_highlights(self, tag_name: str = "highlight"):
        """Clear text highlights"""
        try:
            self.text_widget.tag_delete(tag_name)
        except:
            pass