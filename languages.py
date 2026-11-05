import os
from pygments.lexers import get_lexer_by_name, get_lexer_for_filename
from pygments.lexers.python import PythonLexer
from pygments.util import ClassNotFound

BUILTIN_SERVERS = {
    ".py": "python",
    ".pyw": "python",
    ".pyi": "python",
}

_custom_lexers = {}
_custom_languages = {}

FILE_GROUPS = (
    ("Python", ("py", "pyw", "pyi")),
    ("Text", ("txt", "md", "rst", "log")),
    ("Web", ("html", "htm", "css", "scss", "js", "jsx", "ts", "tsx", "json", "xml", "svg")),
    ("C / C++", ("c", "h", "cpp", "hpp", "cc", "cxx")),
    ("Other source", ("java", "kt", "cs", "go", "rs", "rb", "php", "lua", "sh", "bat", "ps1", "sql", "yaml", "yml", "toml", "ini", "cfg")),
)


def _suffix(path):
    return os.path.splitext(path)[1].lower()


def register(extensions, lexer=None, language=None):
    for ext in extensions:
        ext = ext.lower()
        if not ext.startswith("."):
            ext = "." + ext
        if lexer:
            _custom_lexers[ext] = lexer
        if language:
            _custom_languages[ext] = language


def unregister(extensions):
    for ext in extensions:
        ext = ext.lower()
        if not ext.startswith("."):
            ext = "." + ext
        _custom_lexers.pop(ext, None)
        _custom_languages.pop(ext, None)


def lexer_for(path):
    if not path:
        return PythonLexer(stripnl=False)
    alias = _custom_lexers.get(_suffix(path))
    try:
        if alias:
            return get_lexer_by_name(alias, stripnl=False)
        return get_lexer_for_filename(path, stripnl=False)
    except ClassNotFound:
        return None


def language_for(path):
    if not path:
        return "python"
    suffix = _suffix(path)
    return _custom_languages.get(suffix) or BUILTIN_SERVERS.get(suffix)


def file_filter():
    groups = []
    everything = []
    for label, exts in FILE_GROUPS:
        patterns = " ".join(f"*.{e}" for e in exts)
        everything.append(patterns)
        groups.append(f"{label} ({patterns})")
    for ext in sorted(set(_custom_lexers) | set(_custom_languages)):
        everything.append(f"*{ext}")
    return ";;".join([f"All supported files ({' '.join(everything)})"] + groups + ["All files (*)"])


def language_id(path):
    if not path:
        return "python"
    custom = _custom_languages.get(_suffix(path))
    if custom:
        return custom
    lexer = lexer_for(path)
    if lexer is None or not lexer.aliases:
        return "plaintext"
    return lexer.aliases[0]


def language_name(path):
    if not path:
        return "Python"
    lexer = lexer_for(path)
    if lexer is None:
        return "Plain Text"
    return lexer.name
