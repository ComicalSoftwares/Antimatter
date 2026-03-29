import subprocess
import platform
from tkinter import messagebox, filedialog
import os
def run():
    path = filedialog.askopenfilename(title="Choose file to run", filetypes=[("Python", "*.py"), ("All files", "*.*")])
    if platform.system() == "Windows":
        try:
            subprocess.run(f"python3 {path}", shell=True)
        except Exception as e:
            messagebox.showerror("Run Error", f"Failed to run file:\n{e}")
    elif platform.system() == "Linux":
        try:
            if os.path.exists("/home/.Antimatter/terminal.txt"):
                with open("/home/.Antimatter/terminal.txt", "r", encoding="utf-8") as f:
                    terminal = f.read()
                subprocess.run([f"{terminal} \n python3 {path}"], shell=True)
            else:
                subprocess.run(["x-terminal-emulator", "-e", f"bash -c 'python3 {path}; exec bash'"], shell=True)
        except Exception as e:
            messagebox.showerror("Run Error", f"Failed to run file:\n{e}")

def compile():
    build_template = filedialog.askopenfilename(title="Choose build template to use", filetypes=[("Text file", "*.txt"), ("All files", "*.*")])
    try:
        with open(build_template, "r", encoding="utf-8") as f:
            content = f.read()
        subprocess.run(f"{content}", shell=True)
        messagebox.showinfo("Build Successful", "Build software successful !")
    except Exception as e:
        messagebox.showerror("Build Error", f"Build failed:\n{e}")
