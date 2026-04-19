import customtkinter as ctk
import tkinter as tk
import pygments
from pygments.lexers import PythonLexer
from tklinenums import TkLineNumbers

class AntimatterEditor(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="#16161e", **kwargs)
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # 1. THE TEXT CORE
        self.text = tk.Text(
            self, bg="#16161e", fg="#D8DEE9", insertbackground="white",
            relief="flat", font=("Consolas", 12), undo=True,
            highlightthickness=0, borderwidth=0, wrap="none",
            width=300 # Reduced from 5000 for internal Tcl speed
        )
        self.text.grid(row=0, column=1, sticky="nsew")

        # 2. THE GUTTER (TkLineNumbers)
        self.line_nums = TkLineNumbers(self, self.text, width=50, bg="#16161e", borderwidth=0)
        self.line_nums.grid(row=0, column=0, sticky="ns")

        # 3. THE SCROLLBAR
        self.v_scroll = ctk.CTkScrollbar(self, orientation="vertical", command=self.text.yview)
        self.v_scroll.grid(row=0, column=2, sticky="ns")
        
        # --- THE CHLOROPHYLL MOVE: THE PROXY ---
        # We rename the Tcl command for yview so we can wrap it
        self._orig_yview = self.text._w + "_orig_yview"
        self.tk.call("rename", self.text._w, self._orig_yview)
        self.tk.createcommand(self.text._w, self._proxy_command)

        # Link scrollbar
        self.text.configure(yscrollcommand=self.v_scroll.set)
        
        # Highlighting state
        self._highlight_job = None
        self.setup_theme()

        # Bindings
        self.text.bind("<<Modified>>", self._on_modified)
        self.text.bind("<Configure>", lambda e: self.line_nums.redraw())

    def _proxy_command(self, *args):
        """
        Intercepts EVERY call to the text widget (scrolling, typing, inserting).
        This is exactly how high-performance editors stay in sync.
        """
        # Execute the original command (the actual text action)
        result = self.tk.call(self._orig_yview, *args)

        # If the action was a scroll or a change, redraw line numbers INSTANTLY
        if args[0] in ("yview", "insert", "delete", "replace"):
            self.line_nums.redraw()
            
        return result

    def _on_modified(self, event=None):
        """Triggers when text actually changes"""
        self.line_nums.redraw()
        self.on_key() # Trigger the delayed highlighter
        self.text.edit_modified(False) # Reset the modified flag

    def sync_scroll(self, *args):
        """Used by external calls if needed"""
        self.text.yview(*args)
        self.v_scroll.set(*args)
        self.line_nums.redraw()
    def setup_theme(self):
        theme = {
            "Keyword": "#C594C5", "Name.Builtin": "#6699CC",
            "String": "#99C794",  "Comment": "#A6ACB9",
            "Name.Function": "#5FB3B3", "Operator": "#F99157", "Number": "#F99157"
        }
        for tag, color in theme.items():
            self.text.tag_configure(tag, foreground=color)

    def highlight(self):
        try:
            content = self.text.get("1.0", "end-1c")
            for tag in ["Keyword", "Name.Builtin", "String", "Comment", "Name.Function", "Operator", "Number"]:
                self.text.tag_remove(tag, "1.0", "end")
            
            lexer = PythonLexer()
            offset = 0
            for token, text_val in pygments.lex(content, lexer):
                start = f"1.0+{offset}c"
                end = f"1.0+{offset + len(text_val)}c"
                token_str = str(token)
                if "Keyword" in token_str: self.text.tag_add("Keyword", start, end)
                elif "Builtin" in token_str: self.text.tag_add("Name.Builtin", start, end)
                elif "String" in token_str: self.text.tag_add("String", start, end)
                elif "Comment" in token_str: self.text.tag_add("Comment", start, end)
                elif "Function" in token_str: self.text.tag_add("Name.Function", start, end)
                elif "Operator" in token_str: self.text.tag_add("Operator", start, end)
                elif "Number" in token_str: self.text.tag_add("Number", start, end)
                offset += len(text_val)
        except: pass

    def on_key(self, event=None):
        # 1. Update line numbers IMMEDIATELY (no delay)
        self.line_nums.redraw()
        
        # 2. Debounce the heavy highlighting work
        if self._highlight_job:
            self.after_cancel(self._highlight_job)
        self._highlight_job = self.after(100, self.highlight)

    # Compatibility methods
    def get(self, *args): return self.text.get(*args)
    def delete(self, *args): self.text.delete(*args); self.on_key()
    def insert(self, *args, **kwargs): self.text.insert(*args, **kwargs); self.on_key()
    def yview(self, *args): return self.text.yview(*args)
    def index(self, *args): return self.text.index(*args)

    def edit_reset(self): 
        self.text.edit_reset()

    def edit_modified(self, arg=None):
        return self.text.edit_modified(arg)

    def clear_undo(self):
        self.text.edit_separator()
        self.text.configure(undo=False)
        self.text.configure(undo=True)