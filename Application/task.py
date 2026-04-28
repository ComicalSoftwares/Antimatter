import subprocess
import platform
from tkinter import messagebox, filedialog
import customtkinter as ctk
import threading
import tkterminal

# Run python script (No debugger)
def run():
    path = filedialog.askopenfilename(title="Choose file to run", filetypes=[("Python", "*.py"), ("All files", "*.*")])
    subprocess.run(f"python3 {path}", shell=True)
    
# Compile the script
def compile():
	build_template = filedialog.askopenfilename(title="Choose build template to use", filetypes=[("Text file", "*.txt"), ("All files", "*.*")])
	try:
		with open(build_template, "r", encoding="utf-8") as f:
			content = f.read()
		subprocess.run(f"{content}", shell=True)
		messagebox.showinfo("Build Successful", "Build software successful !")
	except Exception as e:
		messagebox.showerror("Build Error", f"Build failed:\n{e}")
		
# Terminal
def Terminal():
    terminal = ctk.CTk(className="TerminalAntimatter")
    terminal.geometry("700x400")
    terminal.title("Terminal - Comical Antimatter 2026")
    tt = tkterminal.Terminal(terminal, background="black", insertbackground="White", foreground="white")
    tt.pack(side="top", expand=True, fill="both")
    tt.shell = True
    terminal.mainloop()
