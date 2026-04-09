import json
import os
import webbrowser
import platform
import subprocess
from tkinter import filedialog, messagebox
import urllib.request
import re

CURRENT_VERSION = "1.0"

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

def update():
    update_url = "https://api.github.com/repos/ComicalSoftwares/Antimatter/releases/latest"
    try:
       with urllib.request.urlopen(update_url, timeout=10) as resp:
          if resp.status !=200:
              messagebox.showerror("Update", f"Couldn't check for updates (HTTP {resp.status}).")
              return
          data = json.load(resp)
    except Exception as e:
       messagebox.showerror("Update", f"Failed to check for updates: \n{e}")
    latest_tag = data.get("tag_name") or data.get("name") or ""
    latest_version_nums = re.findall(r'\d+', latest_tag)
    current_version_nums = re.findall(r'\d+', CURRENT_VERSION)
    def cmp_ver(a_list, b_list):
       a = [int(x) for x in a_list]
       b = [int(x) for x in b_list]
       L = max(len(a), len(b))
       a += [0] * (L - len(a))
       b += [0] * (L - len(b))
       if a == b:
          return 0
       return 1 if a > b else -1
    if not latest_version_nums:
        if messagebox.askyesno("Update", "Couldn't parse latest release version. Do you want to open pages on Github ?"):
            webbrowser.open(data.get("html_url", "https://github.com/ComicalSoftwares/Antimatter/releases"))
        return
    compare = cmp_ver(latest_version_nums, current_version_nums)
    if compare <= 0:
        messagebox.showinfo("Update", "Antimatter is up-to-date.")
    release_name = data.get("name") or latest_tag
    messagebox.showinfo("Update available", f"Version {release_name} is available for download.")