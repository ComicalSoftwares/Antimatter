# Imports
#===============
import customtkinter as ctk
from tkinter import messagebox, filedialog
import codeview
import pygments.lexers
import CTkMenuBar
from CTkMenuBar import CustomDropdownMenu
import task
import util
from pypresence import Presence
from PIL import Image, ImageTk
import tkterminal
import time
import threading
import subprocess
from pathlib import Path
import platform

# Define dynamic path
#====================
BASE_DIR = Path(__file__).resolve().parent

# Discord Rich Presence 
#========================
client_id = '1487828344480464957'
RPC = Presence(client_id)
def discord():
    try:
        RPC.connect()

        RPC.update( 
            details="Doing absolutely nothing.",
            start=time.time(),
            large_image="image",
            large_text="Antimatter"
        )
    except Exception as e:
        print(f"ERROR: {e}")

# Window configuration
#==========================
app = ctk.CTk(className='Comical')
app.title("Comical Antimatter 2026")
app.geometry("1050x650")
app.configure(fg_color="#16161e")
icon = ImageTk.PhotoImage(Image.open(f"{BASE_DIR}/AppIcon.png"))
app.after(250, lambda: app.iconphoto(False, icon))

# Import Icons for buttons
#=========================
undoI = ctk.CTkImage(light_image=Image.open(f"{BASE_DIR}/redo.png").transpose(Image.FLIP_LEFT_RIGHT))
redoI = ctk.CTkImage(light_image=Image.open(f"{BASE_DIR}/redo.png"))
copyI = ctk.CTkImage(light_image=Image.open(f"{BASE_DIR}/copy.png"))
cutI = ctk.CTkImage(light_image=Image.open(f"{BASE_DIR}/cut.png"))
pasteI = ctk.CTkImage(light_image=Image.open(f"{BASE_DIR}/paste.png"))
termI = ctk.CTkImage(light_image=Image.open(f"{BASE_DIR}/term.png"))
codeI = ctk.CTkImage(light_image=Image.open(f"{BASE_DIR}/code.png"))
issueI = ctk.CTkImage(light_image=Image.open(f"{BASE_DIR}/issue.png"))

# Define Menubar
#==================
menu = CTkMenuBar.CTkMenuBar(app, border_width=0)
menu.configure(fg_color="#16161e")
app.config(menu=menu)

# Editor
#=========
menux = ctk.CTkFrame(app, corner_radius=0)
menux.pack(side="left", expand=True, fill="both")
menux.configure(fg_color="#16161e")

undo = ctk.CTkButton(menux, text="", command=lambda:codeview.event_generate("<<Undo>>"), fg_color="transparent", height=32, width=24, corner_radius=5, image=undoI)
undo.pack(side="top", fill="x")

redo = ctk.CTkButton(menux, text="", command=lambda:codeview.event_generate("<<Redo>>"), fg_color="transparent", height=32, width=24, corner_radius=5, image=redoI)
redo.pack(side="top",fill="x")

copy = ctk.CTkButton(menux, text="", command=lambda:codeview.event_generate("<<Copy>>"), fg_color="transparent", height=32, width=24, corner_radius=5, image=copyI)
copy.pack(side="top", fill="x")

paste= ctk.CTkButton(menux, text="", command=lambda:codeview.event_generate("<<Paste>>"), fg_color="transparent", height=32, width=24, corner_radius=5, image=pasteI)
paste.pack(side="top", fill="x")

cut = ctk.CTkButton(menux, text="", command=lambda:codeview.event_generate("<<Cut>>"), fg_color="transparent", height=32, width=24, corner_radius=5, image=cutI)
cut.pack(side="top", fill="x")

codeview = codeview.AntimatterEditor(app)
codeview.pack(side="left", expand=True, fill="both")

tt = tkterminal.Terminal(app, width=5000, height=4000, background="black", insertbackground="white", foreground="white")
tt.shell = True

# Actions
#========================
current_dir = {"path": None}
def new_file():
    new = messagebox.askyesno("New file", "Save changes made to this file before proceeding ?")
    if new:
        save_file()
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
def open_file(event=None):
    global path
    new = messagebox.askyesno("Open file", "Save changes made to this file before proceeding ?")
    if new:
        save_file()
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
    codeview.edit_reset()
    try:
        RPC.update(
            details = f"Editing {path}",
            large_image="image",
            large_text="Antimatter"
        )
    except Exception:
        pass
def save_file_as(event=None):
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
        with open(path2, "r", encoding="utf-8") as f:
            content = f.read()
        codeview.delete("0.0", "end")
        codeview.insert("0.0", content)
        current_dir["path"] = path2
        app.title(f"{path2} - Comical Antimatter 2026")
    except Exception as e:
        messagebox.showerror("Save Error", f"Could not save file:\n{e}")
        return False
        current_dir["path"] = path2
        return True

def save_file(event=None):
    if not current_dir["path"]:
        return save_file_as()
    try:
        with open(current_dir["path"], "w", encoding="utf-8") as f:
            f.write(codeview.get("0.0", "end-1c"))
    except Exception as e:
        messagebox.showerror("Save Error", f"Could not save file:\n{e}")
        return False
    return True

def Compile(event=None):
    try:
        RPC.update(
            details = "Compiling project",
            large_image = "image",
            large_text = "Antimatter")
    except Exception as e:
        print(e)
        pass
    task.compile()

def Run(event=None):
    try:
        RPC.update(
            details = "Debugging software",
            large_image = "image",
            large_text = "Antimatter")
    except Exception as e:
        print(e)
        pass
    task.run()

def fix_paste(event):
    try:
        text = event.widget.clipboard_get()
        event.widget.insert("insert", text)
        event.widget.see("insert")
    except Exception as e:
        print(e)
        pass
    return "break"

codeview.bind("<Control-v>", fix_paste)
codeview.bind("<<Paste>>", fix_paste)

def restore_codeview(event=None):
    tt.pack_forget()
    codeview.pack(side="left", expand=True, fill="both")
    term.configure(command=terminal, image=termI)

def terminal(event=None):
    codeview.pack_forget()
    tt.pack(side="top", expand=True, fill="both")
    term.configure(command=restore_codeview, image=codeI)

def Drun(event=None):
    terminal()
    path3 = filedialog.askopenfilename(title="Choose file to run", filetypes=[("Python", "*.py"), ("All files", "*.*")])
    if platform.system() == "Windows":
        threading.Thread(target=lambda: tt.run_command(f"python -u {path3}"), daemon=True).start()
    else:
        threading.Thread(target=lambda: tt.run_command(f"python3 -u {path3}"), daemon=True).start()

def issues(event=None):
    iss = ctk.CTk(className="IssuesAntimatter")
    iss.geometry("700x400")
    iss.title("Issues - Comical Antimatter 2026")
    Iis = ctk.CTkTextbox(iss, width=5000, height=4000, state="disabled")
    Iis.pack(side="top", expand=True, fill="both")
    if isinstance(current_dir, dict):
        actual_path = current_dir.get('path', '')
    Out = subprocess.run(f'pyflakes {actual_path}', capture_output=True, text=True, shell=True)
    if Out.stdout == "" and Out.stderr == "":
        Iis.configure(state="normal")
        Iis.insert("0.0", "Nothing wrong with this file. Nice work !")
        Iis.see("end")
        Iis.configure(state="disabled")
    else:
        Iis.configure(state="normal")
        Iis.insert("0.0", Out.stdout + Out.stderr)
        Iis.see("end")
        Iis.configure(state="disabled")
    iss.mainloop()
    
# Special Functions
#===================
term = ctk.CTkButton(menux, text="", command=terminal, fg_color="transparent", height=32, width=24, corner_radius=5, image=termI)
term.pack(side="top", fill="x")
error = ctk.CTkButton(menux, text="", command=issues, fg_color="transparent", height=32, width=24, corner_radius=5, image=issueI)
error.pack(side="top", fill="x")

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
dropdown2.add_option(option="Run", command=Drun)
dropdown2.add_option(option="Run without debugger (Only for GUI apps)", command=Run)
dropdown2.add_option(option="Build project", command=Compile)
dropdown2.add_option(option="Open new terminal window", command=task.Terminal)

# Tools options
dropdown3 = CustomDropdownMenu(widget=Tools)
dropdown3.add_option(option="Open Documentation")
dropdown3.add_option(option="Configure Project", command=util.project)
dropdown3.add_option(option="Update Antimatter", command=util.update)
dropdown3.add_option(option="Reconnect to discord", command=discord)

# Keybinds
#=========
def _bind_focused(seq, func):
    try:
        app.bind(seq, lambda ev, f=func: (f(ev), "break"))
    except Exception:
        try:
            app.bind(seq, lambda ev, f=func: f(ev))
        except Exception:
            pass
binds = [
    (['<Control-s>', '<Control-S>'], save_file),
    (['<Control-Shift-s>', '<Control-Shift-S>'], save_file_as),
    (['<Control-o>', '<Control-O>'], lambda ev: [open_file(), "break"][1]),
    (['<Control-n>', '<Control-N>'], new_file),
    (['<F5>'], Drun),
    (['<Control-F5>'], Compile),
    (['<Control-Shift-c>', '<Control-Shift-c>'], util.project),
    (['<Control-s>', '<Control-S>'], save_file)
]
for seqs, fn in binds:
    for s in seqs:
        _bind_focused(s, fn)

discord()

# Mainloop
#==============
app.mainloop()
