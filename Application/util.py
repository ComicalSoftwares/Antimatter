import json
import os
import webbrowser
import platform
import subprocess
from tkinter import filedialog, messagebox

def project():
    folder = filedialog.askdirectory(title="Choose project folder")
    if folder:
        try:
            subprocess.run(f"cd {folder}", shell=True)
            subprocess.run("python -m venv .venv", shell=True)
            if platform.system() == "Windows":
                subprocess.run(".venv\Scripts\activate", shell=True)
            else:
                subprocess.run("source .venv/bin/activate", shell=True)
            messagebox.showinfo("Done", "Project configured successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Couldn't configure project: \n{e}")
    else:
        pass
        
def docs():
    webbrowser.open("www.github.com/ComicalSoftwares/Antimatter/Wiki")
