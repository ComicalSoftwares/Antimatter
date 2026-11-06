<div align=center>

<img width="241" height="241" alt="AppIcon" src="https://github.com/user-attachments/assets/aecbdeb4-5fc7-4f77-b4b1-908c5e0626d0" />

# Antimatter
A modern, lightweight and absurdly optimized Python IDE written in **Python and PyQT6**
</div>

> [!WARNING]
> Antimatter's current development status is in **early alpha**. We do not recommend you to uninstall your current IDE yet. If you really want to switch then at least wait for it to pass to **Beta stage**.. (which will indeed take a while).

## Features
- Editing and running python scripts
- Compiling scripts by using build templates.
- Clean, distraction-free interface.
- Discord Rich Presence.
- Complete privacy without any telemetry.
- Low resources usage.
- Very snappy UI.
- Shows issues and suggestions **only when you want to see them**. No annoying popups, just **pure programming experience** to help you focus on what matters most.
- Simple to understand wiki and documentation.

## Download today !
Antimatter is free & open-source ! _(Obviously !)_

### Latest release: Version 1.5 - Alpha
- **Windows installer**: [antimatter_setup.exe](https://github.com/ComicalSoftwares/Antimatter/releases/download/1.5/antimatter_setup.exe)
- **Linux**: Learn how to [build from source.](https://github.com/ComicalSoftwares/Antimatter/wiki/Quick-Start-Guide/#installation)

## Libraries and ressources used
- **UI**: PyQT6 & PySide6
- **Code-viewing backend**: Fully custom code-viewer backend, capable of syntax highlighting and loading multiple large scripts in seconds !
- **Rich Presence Framework**: Pypresence
- **Language used**: As said earlier, Python is the main language used for the project.
- **Issues finding**: Using Pyflakes, it can find most problems with the script that may stop it from launching.

## Prerequisites
Antimatter relies on separately installed components/modules to function properly.

These components are:
- **Pyflakes**: For finding issues
- **A working PC**: What ? You thought it was gonna work on a phone ? Be real.
- **Python 3.14**: This is the most recommended version. You can also use any other Python 3.x release with Antimatter, just don't use anything as old as Python 2.x or else the editor will corrupt your files and fail to render them.
- **A compiler (optional)**: If you ship production-ready apps using python, then it is better to have something like "pyinstaller" or "nuitka" installed.
- **Windows/Linux as your main OS**: You need to use Windows/Linux to run Antimatter. You can build the software from source for your OS but we'll provide no form of support in that case (especially with macOS users).

## Screenshots & Demo
>[!Note]
> These screenshots are not definitive and will indeed change as the IDE grows.

<img width="1920" height="1080" alt="Screenshot From 2026-10-10 15-04-57" src="https://github.com/user-attachments/assets/459266d2-c7c0-4cbb-85a4-46940d4834b2" />

<img width="1920" height="1080" alt="Screenshot From 2026-10-11 12-52-13" src="https://github.com/user-attachments/assets/821a88e0-62b6-469e-b66f-f5d7005e8798" />

https://github.com/user-attachments/assets/9cc0926d-c950-440e-9c72-0af109c88957



## Features roadmap
Antimatter is an evolving IDE that targets to satisfy multiple needs !

And to make it satisfy these needs, then we'll have to add all of these necessary features and make them as stable and as reliable as possible.

### Main programming experience:
- [X] Code syntax highlighting.
- [X] Native GPU-accelerated rendering.
- [X] File opening/saving.
- [X] Automated compiling (works by using [build templates](https://github.com/ComicalSoftwares/Antimatter/wiki/Quick-Start-Guide/#building-your-project)).
- [X] Keyboard Shortcuts.
- [X] Issues finder.
- [X] Tabs.
- [ ] LSP and suggestions **(Exists and works but not reliable at the moment)**
### Debugging and managing projects
- [X] File manager.
- [X] Live terminal
- [X] Running Scripts (With and without debugger)
### Customization
- [X] Preferences
- [X] Themes
- [X] Custom fonts
- [X] Modify position of the sidebar (File Manager), the position is now saved
- [X] Extensions (alpha)
### Git support
- [ ] Git clone
- [ ] Git commit
- [ ] Git Push
- [ ] Git Sync
And all of the other essential git functions (whch aren't here yet unfortunately)

## Customization
Open **File > Preferences** (Ctrl+,) or use the command palette (Ctrl+Shift+P, then type "Preferences").

- **Themes:** the color theme styles the editor and the whole interface (sidebar, tabs, menus, status bar, terminal, dialogs). Pick one from Preferences or with Ctrl+K Ctrl+T. More themes come from extensions.
- **Fonts:** choose any installed monospaced font, set the size (also Ctrl + mouse wheel), or add your own `.ttf`, `.otf` or `.ttc` file. Extensions can ship fonts with `contributes.fonts`.
- **Editor:** tab size, word wrap, current line highlight and smooth scrolling.
- **Layout:** the File Manager can sit on the left or the right. Drag it or use Preferences, and its side, width and visibility are remembered, along with the window size.
- **Animations:** springy dialogs, a sliding sidebar, fades and animated buttons and switches. Turn them off in Preferences if you prefer a static interface.

Everything is stored in `~/.antimatter/settings.json`.

## Extensions
Antimatter extensions work like VS Code extensions: a folder with an `extension.json` manifest that contributes commands, keybindings, languages, color themes and snippets, plus a Python entry point that is only loaded when an activation event fires.

- Manage them with **Ctrl+Shift+X**, run commands with the palette (**Ctrl+Shift+P** or **F1**), switch color themes with **Ctrl+K Ctrl+T**.
- Install third party extensions from a `.amext` package (**Extensions > Install Extension from File...**) or by dropping a folder into `~/.antimatter/extensions`.
- Eight extensions are built in (themes, snippets, toggle comment, text tools and more).
- Start your own from `extensions_examples/_template`. The full guide is in `extensions_examples/README.md`.

## Benchmarks
Old version (previous release) against the current one. Median of 3 runs, headless Qt (offscreen), Python 3.12, a 20,000 line Python file, 11 tabs open, `pylsp` installed. Absolute numbers depend on the machine, so compare the ratios.

| Metric | Old | New | Change |
| --- | --- | --- | --- |
| Startup (ms) | 153 | 139 | 1.1x faster |
| Open a 20k line file (ms) | 2262 | 1393 | 1.6x faster |
| Re-highlight 20k lines (ms) | 5534 | 1505 | 3.7x faster |
| Open 10 more tabs (ms) | 331 | 157 | 2.1x faster |
| Memory with 11 tabs (MB, app + children) | 592 | 101 | 5.9x less |
| Child processes | 3 | 1 | language servers start on demand |
| Typing latency, average (ms) | 13.7 | 3.3 | 4.2x faster |
| Typing latency, 95th percentile (ms) | 44.1 | 6.0 | 7.4x faster |

Where the gains come from:
- Highlighting tracks token positions instead of searching the line for each token, and files are no longer highlighted twice on open.
- Language servers start on the first Ctrl+Space instead of at file open, and the full text is sent then, not on every keystroke.
- All editors share one background event loop.
- Extensions are discovered at startup but only imported when an activation event fires.

## Support
Antimatter is indeed full of bugs, we won't lie. And this is why we will happily help you fix these issues via one of these 3 support methods:
- **Discord** (Fastest way of getting support): Visit our home discord server. Suggest, discuss, ask for help and learn about other fun projects we work on ! [Join "Comical Games" on Discord](https://discord.gg/UubHnUNEc7)
- **Wiki** (Contains useful information): We took the time to explain how to use Antimatter and what to expect from the IDE. [Read Antimatter's wiki.](https://github.com/ComicalSoftwares/Antimatter/wiki/Quick-Start-Guide)
- **Github issues** (Slowest way of getting support, manly for bug reports): Github issues is also a good way to get support, but its the slowest method of doing so. You can also use it to report bugs.