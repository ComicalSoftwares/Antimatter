import importlib.util
import json
import re
import shutil
import sys
import traceback
import zipfile
from pathlib import Path
from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QAction, QDesktopServices, QKeySequence
from PyQt6.QtWidgets import QMessageBox

import languages
import lsp
import shapes
import themes

ROOT = Path.home() / ".antimatter"
EXTENSIONS_DIR = ROOT / "extensions"
SETTINGS_FILE = ROOT / "extensions.json"
BUILTIN_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / "builtin_extensions"
MANIFEST = "extension.json"
EVENTS = ("file_opened", "file_saved", "file_closed")


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


class Extension:
    def __init__(self, ext_id, path, manifest, legacy=False, builtin=False):
        self.id = ext_id
        self.path = path
        self.manifest = manifest
        self.legacy = legacy
        self.builtin = builtin
        self.module = None
        self.enabled = False
        self.activated = False
        self.error = None
        self.commands = {}
        self.actions = []
        self.handlers = {}
        self.file_types = []
        self.snippets = {}
        self.command_ids = []
        self.sys_path = None

    @property
    def name(self):
        return self.manifest.get("displayName") or self.manifest.get("name") or self.id

    @property
    def version(self):
        return str(self.manifest.get("version", ""))

    @property
    def publisher(self):
        return self.manifest.get("publisher", "local")

    @property
    def description(self):
        return self.manifest.get("description", "")

    @property
    def events(self):
        if self.legacy:
            return ["*"]
        return list(self.manifest.get("activationEvents", []))

    @property
    def contributes(self):
        return self.manifest.get("contributes", {})

    @property
    def main(self):
        if self.legacy:
            return self.path if self.path.is_file() else self.path / "__init__.py"
        return self.path / self.manifest.get("main", "extension.py")


class CommandsAPI:
    def __init__(self, manager, ext):
        self._manager = manager
        self._ext = ext

    def register(self, command_id, callback, title=None, keybinding=None, category=""):
        self._ext.commands[command_id] = callback
        self._manager.declare_command(self._ext, command_id, title or command_id, category)
        if keybinding:
            self._manager.bind_key(self._ext, command_id, keybinding)

    def execute(self, command_id, *args):
        return self._manager.execute(command_id, *args)

    def list(self):
        return list(self._manager.command_meta)


class ExtensionAPI:
    def __init__(self, manager, ext):
        self._manager = manager
        self._ext = ext
        self.commands = CommandsAPI(manager, ext)

    @property
    def window(self):
        return self._manager.window

    @property
    def extension_path(self):
        return self._ext.path if self._ext.path.is_dir() else self._ext.path.parent

    def add_command(self, title, callback, shortcut=None):
        command_id = f"{self._ext.id}.{slug(title)}"
        self.commands.register(command_id, callback, title, shortcut)
        return command_id

    def add_file_type(self, extensions, lexer=None, language=None):
        languages.register(extensions, lexer, language)
        self._ext.file_types.extend(extensions)

    def add_language_server(self, language, command, extensions=()):
        lsp.register_server(language, command)
        if extensions:
            languages.register(extensions, language=language)
            self._ext.file_types.extend(extensions)

    def on(self, event, callback):
        if event not in EVENTS:
            raise ValueError(f"Unknown event '{event}'. Available events: {', '.join(EVENTS)}")
        self._ext.handlers.setdefault(event, []).append(callback)

    def current_editor(self):
        return self._manager.window.get_current_editor()

    def current_path(self):
        return self._manager.window.get_current_path()

    def open_file(self, path):
        self._manager.window.open_file_by_path(str(path))

    def message(self, text, title=None):
        QMessageBox.information(self._manager.window, title or self._ext.name, str(text))

    def quick_pick(self, items, placeholder, callback):
        entries = [i if isinstance(i, dict) else {"title": str(i)} for i in items]
        self._manager.window.quick_pick(entries, placeholder, callback)


class ExtensionManager:
    def __init__(self, window):
        self.window = window
        self.records = {}
        self.command_meta = {}
        self.keys = {}
        self.menu = None
        self.disabled = self._load_disabled()
        self._snippets = {}

    def _load_disabled(self):
        try:
            return set(json.loads(SETTINGS_FILE.read_text(encoding="utf-8")).get("disabled", []))
        except Exception:
            return set()

    def _save_disabled(self):
        try:
            SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
            SETTINGS_FILE.write_text(json.dumps({"disabled": sorted(self.disabled)}), encoding="utf-8")
        except Exception as e:
            print(f"[Extensions] Could not save settings: {e}")

    def discover(self):
        found = []
        for base, builtin in ((BUILTIN_DIR, True), (EXTENSIONS_DIR, False)):
            if not base.exists():
                if not builtin:
                    base.mkdir(parents=True, exist_ok=True)
                continue
            for entry in sorted(base.iterdir()):
                if entry.name.startswith((".", "_")):
                    continue
                manifest_path = entry / MANIFEST
                if entry.is_dir() and manifest_path.exists():
                    try:
                        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                        ext_id = f"{manifest.get('publisher', 'local')}.{manifest['name']}"
                        found.append(Extension(ext_id, entry, manifest, builtin=builtin))
                    except Exception as e:
                        broken = Extension(entry.name, entry, {"name": entry.name}, builtin=builtin)
                        broken.error = f"Invalid {MANIFEST}: {e}"
                        found.append(broken)
                elif (entry.is_file() and entry.suffix == ".py") or (entry.is_dir() and (entry / "__init__.py").exists()):
                    stem = entry.stem if entry.is_file() else entry.name
                    found.append(Extension(stem, entry, {"name": stem}, legacy=True, builtin=builtin))
        return found

    def build_menu(self, menubar):
        self.menu = shapes.round_menu(menubar.addMenu("Extensions"))
        self.menu.addAction("Manage Extensions...", self.window.show_extensions_panel)
        self.menu.addAction("Install Extension from File...", self.window.install_extension_dialog)
        self.menu.addSeparator()
        self.menu.addAction("Reload Extensions", self.reload_all)
        self.menu.addAction("Open Extensions Folder", self.open_folder)

    def open_folder(self):
        EXTENSIONS_DIR.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(EXTENSIONS_DIR)))

    def load_all(self):
        for ext in self.discover():
            self.records[ext.id] = ext
            if ext.error:
                continue
            if ext.id in self.disabled:
                continue
            self._enable(ext)
        QTimer.singleShot(400, lambda: self.activate_event("onStartupFinished"))

    def reload_all(self):
        for ext in list(self.records.values()):
            self._disable(ext)
        self.records.clear()
        for name in [m for m in sys.modules if m.startswith("antimatter_ext_")]:
            del sys.modules[name]
        self.load_all()
        themes.restore()
        self.window.apply_theme()

    def _enable(self, ext):
        ext.enabled = True
        ext.error = None
        try:
            self._contribute(ext)
        except Exception:
            ext.error = traceback.format_exc()
            print(f"[Extensions] Failed to read contributions of {ext.id}:\n{ext.error}")
        if ext.legacy or "*" in ext.events:
            self.activate(ext)

    def _disable(self, ext):
        if ext.activated and ext.module is not None and hasattr(ext.module, "deactivate"):
            try:
                ext.module.deactivate()
            except Exception:
                print(f"[Extensions] Error while deactivating {ext.id}:\n{traceback.format_exc()}")
        for action in ext.actions:
            self.window.removeAction(action)
            action.deleteLater()
        for command_id in ext.command_ids:
            self.command_meta.pop(command_id, None)
            self.keys.pop(command_id, None)
        languages.unregister(ext.file_types)
        themes.unregister_source(ext.id)
        if ext.sys_path and ext.sys_path in sys.path:
            sys.path.remove(ext.sys_path)
        ext.actions.clear()
        ext.commands.clear()
        ext.handlers.clear()
        ext.file_types.clear()
        ext.snippets.clear()
        ext.command_ids.clear()
        ext.module = None
        ext.sys_path = None
        ext.activated = False
        ext.enabled = False
        self._rebuild_snippets()

    def _contribute(self, ext):
        c = ext.contributes
        for entry in c.get("commands", []):
            self.declare_command(ext, entry["command"], entry.get("title", entry["command"]), entry.get("category", ""))
        for entry in c.get("keybindings", []):
            self.bind_key(ext, entry["command"], entry["key"])
        for entry in c.get("languages", []):
            exts = entry.get("extensions", [])
            languages.register(exts, entry.get("lexer"), entry.get("id"))
            ext.file_types.extend(exts)
            if entry.get("server"):
                lsp.register_server(entry["id"], entry["server"])
        for entry in c.get("themes", []):
            theme = themes.load_file(ext.path / entry["path"])
            themes.register(theme, ext.id, entry.get("label"))
        for entry in c.get("snippets", []):
            data = json.loads((ext.path / entry["path"]).read_text(encoding="utf-8"))
            table = ext.snippets.setdefault(entry["language"], {})
            for snippet in data.values():
                prefixes = snippet.get("prefix", [])
                for prefix in ([prefixes] if isinstance(prefixes, str) else prefixes):
                    table[prefix] = snippet.get("body", "")
        self._rebuild_snippets()

    def _rebuild_snippets(self):
        merged = {}
        for ext in self.records.values():
            if ext.enabled:
                for language, table in ext.snippets.items():
                    merged.setdefault(language, {}).update(table)
        self._snippets = merged

    def snippet_for(self, language, prefix):
        return self._snippets.get(language, {}).get(prefix)

    def declare_command(self, ext, command_id, title, category=""):
        self.command_meta[command_id] = {"title": title, "category": category, "ext": ext}
        if command_id not in ext.command_ids:
            ext.command_ids.append(command_id)

    def bind_key(self, ext, command_id, key):
        action = QAction(self.window)
        action.setShortcut(QKeySequence(key))
        action.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        action.triggered.connect(lambda checked=False: self.execute(command_id))
        self.window.addAction(action)
        ext.actions.append(action)
        self.keys[command_id] = QKeySequence(key).toString(QKeySequence.SequenceFormat.NativeText)

    def activate(self, ext):
        if ext.activated:
            return True
        if not ext.enabled:
            return False
        try:
            module_name = f"antimatter_ext_{slug(ext.id)}"
            main = ext.main
            if not main.exists():
                raise FileNotFoundError(f"Entry point not found: {main}")
            ext.sys_path = str(main.parent)
            if ext.sys_path not in sys.path:
                sys.path.insert(0, ext.sys_path)
            kwargs = {}
            if main.name == "__init__.py":
                kwargs["submodule_search_locations"] = [str(main.parent)]
            spec = importlib.util.spec_from_file_location(module_name, main, **kwargs)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            ext.module = module
            if ext.legacy:
                ext.manifest.update({
                    "displayName": getattr(module, "NAME", ext.id),
                    "version": str(getattr(module, "VERSION", "")),
                    "description": getattr(module, "DESCRIPTION", ""),
                })
            if not hasattr(module, "activate"):
                raise AttributeError("Extension has no activate(api) function")
            module.activate(ExtensionAPI(self, ext))
            ext.activated = True
            ext.error = None
            return True
        except Exception:
            ext.error = traceback.format_exc()
            print(f"[Extensions] Failed to activate {ext.id}:\n{ext.error}")
            return False

    def activate_event(self, event):
        for ext in list(self.records.values()):
            if ext.enabled and not ext.activated and event in ext.events:
                self.activate(ext)

    def execute(self, command_id, *args):
        meta = self.command_meta.get(command_id)
        if meta is None:
            QMessageBox.warning(self.window, "Command not found", f"No command named '{command_id}' is registered.")
            return None
        ext = meta["ext"]
        if not ext.activated and not self.activate(ext):
            QMessageBox.warning(self.window, "Extension error", f"{ext.name} could not be activated.")
            return None
        handler = ext.commands.get(command_id)
        if handler is None:
            QMessageBox.warning(self.window, "Command not found", f"{ext.name} did not register '{command_id}'.")
            return None
        return self.run_safely(ext, handler, *args)

    def palette_items(self):
        items = []
        for command_id, meta in self.command_meta.items():
            title = f"{meta['category']}: {meta['title']}" if meta["category"] else meta["title"]
            items.append({"title": title, "key": self.keys.get(command_id, ""), "command": command_id})
        return items

    def set_enabled(self, ext, state):
        if state and not ext.enabled:
            self.disabled.discard(ext.id)
            self._enable(ext)
        elif not state and ext.enabled:
            self.disabled.add(ext.id)
            self._disable(ext)
        self._save_disabled()

    def install(self, source):
        source = Path(source)
        staging = ROOT / ".staging"
        shutil.rmtree(staging, ignore_errors=True)
        staging.mkdir(parents=True, exist_ok=True)
        try:
            if source.is_dir():
                shutil.copytree(source, staging / source.name)
            else:
                with zipfile.ZipFile(source) as archive:
                    for member in archive.namelist():
                        target = (staging / member).resolve()
                        if staging.resolve() not in target.parents and target != staging.resolve():
                            raise ValueError(f"Unsafe path in package: {member}")
                    archive.extractall(staging)
            roots = [staging] + [p for p in staging.iterdir() if p.is_dir()]
            package_dir = next((p for p in roots if (p / MANIFEST).exists()), None)
            if package_dir is None:
                raise ValueError(f"No {MANIFEST} found in the package")
            manifest = json.loads((package_dir / MANIFEST).read_text(encoding="utf-8"))
            ext_id = f"{manifest.get('publisher', 'local')}.{manifest['name']}"
            dest = EXTENSIONS_DIR / ext_id
            EXTENSIONS_DIR.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                self._disable_by_id(ext_id)
                shutil.rmtree(dest)
            shutil.copytree(package_dir, dest)
            self.disabled.discard(ext_id)
            self._save_disabled()
        finally:
            shutil.rmtree(staging, ignore_errors=True)
        self.reload_all()
        return ext_id

    def _disable_by_id(self, ext_id):
        ext = self.records.get(ext_id)
        if ext:
            self._disable(ext)

    def uninstall(self, ext):
        if ext.builtin:
            return False
        self._disable(ext)
        if ext.path.is_dir():
            shutil.rmtree(ext.path, ignore_errors=True)
        else:
            ext.path.unlink(missing_ok=True)
        self.disabled.discard(ext.id)
        self._save_disabled()
        self.reload_all()
        return True

    def run_safely(self, ext, callback, *args, **kwargs):
        try:
            return callback(*args, **kwargs)
        except Exception:
            print(f"[Extensions] Error in {ext.id}:\n{traceback.format_exc()}")
            QMessageBox.warning(self.window, "Extension error", f"{ext.name} raised an error:\n{traceback.format_exc().splitlines()[-1]}")

    def emit(self, event, **payload):
        for ext in list(self.records.values()):
            for callback in list(ext.handlers.get(event, [])):
                try:
                    callback(**payload)
                except Exception:
                    print(f"[Extensions] Error in {ext.id} ({event}):\n{traceback.format_exc()}")
