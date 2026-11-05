# Writing an Antimatter extension

Antimatter extensions follow the same model as VS Code: a folder with an `extension.json` manifest, a Python entry point, and a `contributes` section that declares what the extension adds. Contributions are registered at startup without running any code. The entry point is only imported when one of its activation events fires.

## Quick start

1. Copy `_template/` to `~/.antimatter/extensions/me.my-extension/` (the folder name can be anything).
2. Edit `extension.json` and `extension.py`.
3. Press Ctrl+Shift+X, then Reload. Run your command from the palette with Ctrl+Shift+P.

To share an extension, zip the folder contents (with `extension.json` at the root) and rename it to `.amext`. Others install it from **Extensions > Install Extension from File...**.

## Manifest

| Field | Purpose |
| --- | --- |
| `name`, `publisher`, `version` | Identify the extension. The id is `publisher.name` |
| `displayName`, `description` | Shown in the Extensions panel |
| `main` | Entry point relative to the folder (default `extension.py`) |
| `activationEvents` | `*`, `onStartupFinished`, `onLanguage:<id>`, `onCommand:<id>` |
| `contributes.commands` | `{command, title, category}` entries shown in the palette |
| `contributes.keybindings` | `{command, key}` entries, for example `"Ctrl+Alt+H"` |
| `contributes.languages` | `{id, extensions, lexer, server}`: file types, Pygments lexer, optional language server command |
| `contributes.themes` | `{label, path}`: color theme JSON files |
| `contributes.snippets` | `{language, path}`: VS Code style snippet JSON files, expanded with Tab |

An extension without `activationEvents` is only activated through a command that something else invokes.

## Entry point

`activate(api)` is required, `deactivate()` is optional.

| Call | What it does |
| --- | --- |
| `api.commands.register(id, callback, title=None, keybinding=None, category="")` | Registers a command handler |
| `api.commands.execute(id, *args)` | Runs any command, activating its extension if needed |
| `api.on(event, callback)` | Events: `file_opened(editor, path)`, `file_saved(editor, path)`, `file_closed(path)` |
| `api.current_editor()` | Active editor or `None`. `.text` is the QPlainTextEdit, `.get()` returns the text |
| `api.current_path()` | Path of the active file or `None` |
| `api.open_file(path)` | Opens a file in a tab |
| `api.message(text, title=None)` | Info dialog |
| `api.quick_pick(items, placeholder, callback)` | Palette style list. Items are strings or dicts with `title` and optional `key` |
| `api.add_file_type(...)`, `api.add_language_server(...)` | Dynamic versions of the language contributions |
| `api.extension_path`, `api.window` | Extension folder and main window |

Errors in an extension are caught and shown, so a broken extension can't crash the editor.

## Themes

Theme files use `colors` (`editor.background`, `editor.foreground`, `editor.selectionBackground`, `editor.lineHighlightBackground`, `editorLineNumber.foreground`, `editorLineNumber.activeForeground`) and `tokenColors` (`keyword`, `string`, `comment`, `number`, `operator`, `function`, `class`, `builtin`, `namespace`, `tag`). Missing values fall back to the defaults for the theme `type`. Many VS Code theme files also work: `tokenColors` may be a list of `{scope, settings.foreground}` rules.

## Single-file extensions

A plain `.py` file (or a package folder with `__init__.py`) in the extensions folder still works. It is activated at startup and may use `api.add_command(title, callback, shortcut)`, plus `NAME`, `VERSION` and `DESCRIPTION` module variables.

## Built-in extensions

Antimatter ships with `toggle-comment`, `text-tools`, `todo-finder`, `reopen-closed`, `word-count`, `file-types`, `snippets` and `themes` in `builtin_extensions/`. They are good references and can be disabled from the Extensions panel.
