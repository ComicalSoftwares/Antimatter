import subprocess
import platform
from tkinter import messagebox, filedialog
import customtkinter as ctk
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Run python script (No debugger)
def run():
    path = filedialog.askopenfilename(title="Choose file to run", filetypes=[("Python", "*.py"), ("All files", "*.*")])
    if platform.system() == "Windows":
         subprocess.run(f"python {path}", shell=True)
    else:
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
    def command(event=None):
        en = entry.get()
        if not en: return 
    
        output.configure(state="normal")
        output.insert("end", f"\n> {en}\n")
    
        try:
           out = subprocess.run(en, shell=True, capture_output=True, text=True)
           resultat = out.stdout + out.stderr
           output.insert("end", resultat)
        except Exception as e:
           output.insert("end", f"Erreur : {str(e)}")
        
        output.insert("end", "\n")
        output.configure(state="disabled")
        output.see("end")
        entry.delete(0, "end")
    
    terminal = ctk.CTk()
    terminal.geometry("750x600")
    terminal.title("Terminal - Comical Antimatter 2026")
    terminal.iconbitmap(f"{BASE_DIR}/AppIcon.ico")

    output = ctk.CTkTextbox(terminal, width=500, height=400, state="disabled")
    output.pack(side="top", expand=True, fill="both", padx=10, pady=5)

    entry = ctk.CTkEntry(terminal, width=500, placeholder_text="Type a command")
    entry.pack(side="bottom", fill="x", padx=10, pady=10)
    entry.unbind("<Return>")
    entry.bind("<Return>", command)

    terminal.mainloop()