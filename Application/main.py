# Imports
#===============
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
from codeview import *
import pygments.lexers
from CTkMenuBar import *
import os
import task
import util
from pypresence import Presence
import time

# Discord Rich Presence
#========================
client_id = '1487828344480464957'
RPC = Presence(client_id)
try:
    RPC.connect()

    RPC.update( 
        details="Doing absolutely nothing",
        start=time.time(),
        large_image="image",
        large_text="Antimatter"
    )
except Exception as e:
    print(f"ERROR: {e}")
    pass
# Window configuration
#==========================

app = ctk.CTk()
app.title("Comical Antimatter 2026")
app.geometry("1050x650")

# Define Menubar
#==================
menu = CTkMenuBar(app)
menu.configure(fg_color="#292827")
app.config(menu=menu)

# Editor
#=========
editor = ctk.CTkFrame(app)
editor.pack(side="top", fill="both")
editor.configure(fg_color="#292827")
codeview = CodeView(editor, lexer=pygments.lexers.PythonLexer, color_scheme="mariana", height=200, font=("Consolas", 11))
codeview.pack(side="top", fill="both", expand=True, padx=5, pady=5)

# File management logic
#========================
current_dir = {"path": None}
def new_file():
    new = messagebox.askyesno("New file", "Save changes made to this file before proceeding ?")
    if new:
        save_file()
        codeview.delete("0.0", "end")
        current_dir["path"] = None
        app.title("Comical Antimatter 2026")
    else:
        codeview.delete("0.0", "end")
        current_dir["path"] = None
        app.title("Comical Antimatter 2026")
    try:
        RPC.update(
            details = "Editing an unnamed file",
            large_image="image",
            large_text="Antimatter"
        )
    except Exception:
        pass

def open_file():
    global path
    new = messagebox.askyesno("Open file", "Save changes made to this file before proceeding ?")
    if new:
        save_file()
    else:
        pass
    path = filedialog.askopenfilename(title="Open file", filetypes=[("Python", "*.py"), ("Text", "*.txt"), ("All files", "*.*")])
    if not path:
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        messagebox.showerror("Open Error", f"Could not open file:\n{e}")
        return
    codeview.delete("0.0", "end")
    codeview.insert("0.0", content)
    current_dir["path"] = path
    app.title(f"{path} - Comical Antimatter 2026")
    try:
        RPC.update(
            details = f"Editing {path}",
            large_image="image",
            large_text="Antimatter"
        )
    except Exception:
        pass
def save_file_as():
    path2 = filedialog.asksaveasfilename(
            title="Save file As",
            defaultextension=".py",
            filetypes=[("Python", "*.py"), ("Text", "*.txt"), ("All files", "*.*")]
        )
    if not path2:
        return False
    try:
        with open(path2, "w", encoding="utf-8") as f:
            f.write(codeview.get("0.0", "end-1c"))
    except Exception as e:
        messagebox.showerror("Save Error", f"Could not save file:\n{e}")
        return False
        current_dir["path"] = path
        return True

def save_file():
    if not current_dir["path"]:
        return save_file_as()
    try:
        with open(current_dir["path"], "w", encoding="utf-8") as f:
            f.write(codeview.get("0.0", "end-1c"))
    except Exception as e:
        messagebox.showerror("Save Error", f"Could not save file:\n{e}")
        return False
    return True

# Add cascades
#================
File = menu.add_cascade("File")
Task = menu.add_cascade("Task")
Tools = menu.add_cascade("Tools")

# Add options
#=============

# File options
dropdown1 = CustomDropdownMenu(widget=File)
dropdown1.add_option(option="New File", command=new_file)
dropdown1.add_option(option="Open File", command=open_file)
dropdown1.add_option(option="Save", command=save_file)
dropdown1.add_option(option="Save As", command=save_file_as)

# Task options
dropdown2 = CustomDropdownMenu(widget=Task)
dropdown2.add_option(option="Run", command=
    task.run,
)
dropdown2.add_option(option="Build project", command=
    task.compile
)

# Tools options
dropdown3 = CustomDropdownMenu(widget=Tools)
dropdown3.add_option(option="Open Documentation")
dropdown3.add_option(option="Configure Project", command=util.project)

 # Keybinds
 #=========
def _bind_focused(seq, func):
    try:
        app.bind(seq, lambda ev, f=func: (f(), "break"))
    except Exception:
        try:
            app.bind(seq, lambda ev, f=func: f())
        except Exception:
            pass
binds = [
    (['<Control-s>', '<Control-S>'], save_file),
    (['<Control-Shitf-s>', '<Control-Shift-S>'], save_file_as),
    (['<Control-o>', '<Control-O>'], open_file),
    (['<Control-n>', '<Control-N>'], new_file),
    (['<F5>'], task.run),
    (['<Control-F5>'], task.compile),
    (['<Control-Shift-c>', '<Control-Shift-c>'], util.project),
    (['<Control-s>', '<Control-S>'], save_file)
]
for seqs, fn in binds:
    for s in seqs:
        _bind_focused(s, fn)

# Mainloop
#==============
app.mainloop()
