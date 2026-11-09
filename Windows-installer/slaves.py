# Called it slaves.py because its just the backend made by some slaves
import sys
import os
import shutil
import subprocess
import platform
import winreg
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal

def get_installation_directory(scope: str) -> Path:
    if scope == "system":
        return Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "ComicalSoftwares" / "Antimatter"
    return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "Programs" / "ComicalSoftwares" / "Antimatter"

def copy_application_files(target_dir: Path, base_dir: Path, icon_path: str) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    
    source_binary = Path(sys.executable) if getattr(sys, 'frozen', False) else base_dir / "main.py"
    dest_binary = target_dir / ("antimatter.exe" if platform.system() == "Windows" else "antimatter")

    if getattr(sys, 'frozen', False):
        shutil.copy2(source_binary, dest_binary)
    else:
        shutil.copy2(source_binary, target_dir / "main.py")

    if os.path.exists(icon_path):
        shutil.copy2(icon_path, target_dir / "AppIcon.png")

    return dest_binary

def create_start_menu_shortcut(target_binary: Path, scope: str):
    if platform.system() != "Windows":
        return

    if scope == "system":
        start_menu_path = Path(os.environ.get("PROGRAMDATA", "C:\\ProgramData")) / "Microsoft\\Windows\\Start Menu\\Programs"
    else:
        start_menu_path = Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming")) / "Microsoft\\Windows\\Start Menu\\Programs"

    shortcut_dir = start_menu_path / "ComicalSoftwares"
    shortcut_dir.mkdir(parents=True, exist_ok=True)
    shortcut_file = shortcut_dir / "Antimatter.lnk"

    vbs_script = f"""
    Set WshShell = WScript.CreateObject("WScript.Shell")
    Set shortcut = WshShell.CreateShortcut("{shortcut_file}")
    shortcut.TargetPath = "{target_binary}"
    shortcut.WorkingDirectory = "{target_binary.parent}"
    shortcut.IconLocation = "{target_binary.parent / 'AppIcon.png'}"
    shortcut.Description = "Comical Antimatter IDE / Editor"
    shortcut.Save
    """
    script_path = target_binary.parent / "temp_shortcut.vbs"
    script_path.write_text(vbs_script, encoding="utf-8")
    subprocess.run(["cscript", "//Nologo", str(script_path)], shell=True, check=False)
    if script_path.exists():
        script_path.unlink()

def register_file_associations(target_binary: Path):
    if platform.system() != "Windows":
        return

    app_command = f'"{target_binary}" "%1"'
    extensions = [
        (".py", "Antimatter.PythonFile"),
        (".md", "Antimatter.MarkdownFile"),
        (".txt", "Antimatter.TextFile")
    ]

    for ext, prog_id in extensions:
        try:
            winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{ext}")
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{ext}", 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValue(key, "", winreg.REG_SZ, prog_id)

            winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{prog_id}\\shell\\open\\command")
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{prog_id}\\shell\\open\\command", 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValue(key, "", winreg.REG_SZ, app_command)
        except Exception as e:
            print(f"[Registry Warning] Failed to register extension {ext}: {e}")

    try:
        folder_cmd_path = "Software\\Classes\\Directory\\shell\\AntimatterOpen\\command"
        winreg.CreateKey(winreg.HKEY_CURRENT_USER, folder_cmd_path)
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, folder_cmd_path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValue(key, "", winreg.REG_SZ, app_command)
            
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Software\\Classes\\Directory\\shell\\AntimatterOpen", 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValue(key, "", winreg.REG_SZ, "Open with Antimatter")
    except Exception as e:
        print(f"[Registry Warning] Failed to register folder context menu: {e}")

def install_optional_dependencies(deps: list, progress_callback=None):
    for dep in deps:
        if progress_callback:
            progress_callback(f"Installing component: {dep}...")
        
        if dep == "pyflakes":
            subprocess.run([sys.executable, "-m", "pip", "install", "pyflakes"], capture_output=True, text=True, check=False)
        elif dep == "git":
            subprocess.run(["winget", "install", "--id", "Git.Git", "-e", "--source", "winget", "--accept-package-agreements"], capture_output=True, text=True, check=False)

class InstallWorker(QThread):
    progress_updated = pyqtSignal(str, int)
    finished = pyqtSignal(bool, str)

    def __init__(self, scope: str, install_deps: list, base_dir: Path, icon_path: str):
        super().__init__()
        self.scope = scope
        self.install_deps = install_deps
        self.base_dir = base_dir
        self.icon_path = icon_path

    def run(self):
        try:
            self.progress_updated.emit("Configuring installation paths...", 10)
            target_dir = get_installation_directory(self.scope)

            self.progress_updated.emit("Copying binary files...", 30)
            target_binary = copy_application_files(target_dir, self.base_dir, self.icon_path)

            self.progress_updated.emit("Creating Start Menu shortcuts...", 50)
            create_start_menu_shortcut(target_binary, self.scope)

            self.progress_updated.emit("Registering file associations...", 70)
            register_file_associations(target_binary)

            if self.install_deps:
                self.progress_updated.emit("Installing dependencies...", 85)
                install_optional_dependencies(self.install_deps, lambda msg: self.progress_updated.emit(msg, 90))

            self.progress_updated.emit("Finalizing setup...", 100)
            self.finished.emit(True, f"Antimatter has been installed to:\n{target_dir}")
        except Exception as e:
            self.finished.emit(False, str(e))