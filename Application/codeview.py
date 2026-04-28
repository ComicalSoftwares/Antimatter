import customtkinter as ctk
import tkinter as tk
import threading
import queue
from pygments.lexers import PythonLexer
from pygments import lex
from tklinenums import TkLineNumbers

class AntimatterEditor(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="#16161e", width=300, **kwargs)
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 1. THE TEXT CORE
        self.text = tk.Text(
            self, bg="#16161e", fg="#D8DEE9", insertbackground="white",
            relief="flat", font=("Consolas", 12), undo=True,
            highlightthickness=0, borderwidth=0, wrap="none",
            padx=10, pady=10, inactiveselectbackground="#2e3c64", width=300
        )
        self.text.grid(row=0, column=1, sticky="nsew")

        # 2. THE GUTTER (Borderwidth 0)
        self.line_nums = TkLineNumbers(
            self, self.text, width=45, bg="#16161e", 
            borderwidth=0, highlightthickness=0, justify="center"
        )
        self.line_nums.grid(row=0, column=0, sticky="ns")

        # 3. THE SCROLLBAR
        self.v_scroll = ctk.CTkScrollbar(self, orientation="vertical", command=self.text.yview)
        self.v_scroll.grid(row=0, column=2, sticky="ns")
        self.text.configure(yscrollcommand=self.v_scroll.set)

        # 4. DARK CONTEXT MENU
        self.context_menu = tk.Menu(
            self.text, tearoff=0, bg="#191c20", fg="#D8DEE9", 
            activebackground="#455765", activeforeground="white", 
            bd=0, font=("Segoe UI", 10), borderwidth=0
        )
        self._build_context_menu()

        # 5. THE ENGINE
        self.lexer = PythonLexer()
        self.highlighter_queue = queue.Queue()
        self._highlight_job = None
        
        # Start systems
        self.after(1, self._init_logic)

    def _init_logic(self):
        self._setup_theme()
        self._setup_proxy()
        threading.Thread(target=self._highlighter_worker, daemon=True).start()
        self.text.bind("<Button-3>", self._show_context_menu)
        self.trigger_highlight()

    def _setup_theme(self):
        """High-contrast theme mapping for Pygments tokens."""
        self.theme_map = {
            "Token.Keyword": "#c678dd", 
            "Token.Name.Function": "#61afef",
            "Token.Literal.String": "#98c379", 
            "Token.Comment": "#5c6370",
            "Token.Operator": "#56b6c2", 
            "Token.Literal.Number": "#d19a66",
            "Token.Name.Builtin": "#e5c07b",
            "Token.Name.Namespace": "#61afef",
            "Token.Name.Class": "#e5c07b"
        }
        for token, color in self.theme_map.items():
            self.text.tag_configure(token, foreground=color)

    def _setup_proxy(self):
        self._orig = self.text._w + "_orig"
        self.tk.call("rename", self.text._w, self._orig)
        self.tk.createcommand(self.text._w, self._proxy)

    def _proxy(self, *args):
        try:
            result = self.tk.call(self._orig, *args)
        except tk.TclError as e:
            if "tagged with \"sel\"" in str(e): return ""
            raise e
      
        if args[0] in ("insert", "delete", "replace", "yview"):
            self.line_nums.redraw()
            self.trigger_highlight() 
        return result

    def _build_context_menu(self):
        self.context_menu.add_command(label="Cut", command=lambda: self.text.event_generate("<<Cut>>"))
        self.context_menu.add_command(label="Copy", command=lambda: self.text.event_generate("<<Copy>>"))
        self.context_menu.add_command(label="Paste", command=lambda: self.text.event_generate("<<Paste>>"))
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Select All", command=lambda: self.text.tag_add("sel", "1.0", "end"))

    def _show_context_menu(self, event):
        self.context_menu.post(event.x_root, event.y_root)

    def trigger_highlight(self):
        """Debounce highlighting to 20ms for snappiness."""
        if self._highlight_job:
            self.after_cancel(self._highlight_job)
        self._highlight_job = self.after(20, self._request_highlight)

    def _request_highlight(self):
        try:
            visible_start = self.text.index("@0,0 linestart")
            lookback_index = self.text.index(f"{visible_start} - 100 lines linestart")
            
            if self.text.compare(lookback_index, "<", "1.0"):
                lookback_index = "1.0"
                
            end = self.text.index(f"@0,{self.text.winfo_height()} lineend + 100 lines")
            content = self.text.get(lookback_index, end)
            
            self.highlighter_queue.put((lookback_index, content))
        except Exception:
            pass

    def _highlighter_worker(self):
        while True:
            start_index, content = self.highlighter_queue.get()
            tags_to_apply = []
            offset = 0
            
            for token, value in lex(content, self.lexer):
                token_str = f"Token.{token}"
                matched_tag = next((t for t in self.theme_map.keys() if t in token_str), None)
                
                if matched_tag:
                    t_start = f"{start_index}+{offset}c"
                    t_end = f"{start_index}+{offset + len(value)}c"
                    tags_to_apply.append((matched_tag, t_start, t_end))
                offset += len(value)
            
            self.after(0, lambda t=tags_to_apply, s=start_index, e=f"{start_index}+{len(content)}c": 
                       self._apply_tags(t, s, e))

    def _apply_tags(self, tags, range_start, range_end):
        for tag in self.theme_map.keys():
            self.text.tag_remove(tag, range_start, range_end)
        for tag, start, end in tags:
            self.text.tag_add(tag, start, end)

    def get(self, *args): return self.text.get(*args)
    def insert(self, *args, **kwargs): 
        self.text.insert(*args, **kwargs)
        self.trigger_highlight()
    def delete(self, *args): 
        self.text.delete(*args)
        self.trigger_highlight()
    def edit_reset(self): self.text.edit_reset()
    def edit_modified(self, arg=None): return self.text.edit_modified(arg)
    def tag_add(self, *args): self.text.tag_add(*args)
    def event_generate(self, *args, **kwargs): self.text.event_generate(*args, **kwargs)