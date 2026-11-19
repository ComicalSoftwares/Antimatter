import asyncio
import json
import os
import sys
from pathlib import Path

LANG_SERVERS = {
    "python": [sys.executable, "-m", "pylsp"],
}

# Antimatter shows issues through ruff, so pylsp's own linters would only add latency.
PYLSP_PLUGINS = {
    "pycodestyle": {"enabled": False},
    "pyflakes": {"enabled": False},
    "mccabe": {"enabled": False},
    "autopep8": {"enabled": False},
    "yapf": {"enabled": False},
    "pylint": {"enabled": False},
}


def path_to_uri(path):
    return Path(path).resolve().as_uri()


def _find_venv_python(root_path):
    root = Path(root_path).resolve()
    for folder in [root, *root.parents][:4]:
        for rel in ("bin/python", "Scripts/python.exe"):
            candidate = folder / ".venv" / rel
            if candidate.exists():
                return str(candidate)
    return None


class LspClient:
    INIT_TIMEOUT = 20       # first start can be slow
    REQUEST_TIMEOUT = 5
    COMPLETE_TIMEOUT = 3
    MAX_COMPLETIONS = 200

    def __init__(self):
        self._proc = None
        self._id = 0
        self._pending = {}
        self._reader_task = None
        self._version = 0
        self._uri = None
        self._language = None
        self._loop = None
        self._ready = False
        self._start_lock = None

    @property
    def alive(self):
        return self._proc is not None and self._proc.returncode is None

    @property
    def running(self):
        return self._ready and self.alive

    async def start(self, language, root_path):
        if self._start_lock is None:
            self._start_lock = asyncio.Lock()
        async with self._start_lock:
            if self.running:
                return True
            await self.stop()          # clean up any half-started leftovers
            return await self._start(language, root_path)

    async def _start(self, language, root_path):
        cmd = LANG_SERVERS.get(language)
        if not cmd:
            print(f"[LSP] No language server configured for '{language}'.")
            return False

        self._loop = asyncio.get_running_loop()
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
        except Exception as e:
            print(f"[LSP] Failed to launch the language server: {e}")
            return False

        self._proc = proc
        self._language = language
        self._reader_task = self._loop.create_task(self._read_loop(proc))

        result = await self._request("initialize", {
            "processId": os.getpid(),
            "rootUri": path_to_uri(root_path),
            "capabilities": {
                "textDocument": {
                    "completion": {"completionItem": {"snippetSupport": False}},
                },
                "workspace": {"configuration": True},
            },
        }, timeout=self.INIT_TIMEOUT)

        if result is None:
            print("[LSP] The server didn't answer 'initialize'. "
                  "Is python-lsp-server installed?")
            await self.stop()
            return False

        await self._notify("initialized", {})

        settings = {"plugins": dict(PYLSP_PLUGINS)}
        venv_python = _find_venv_python(root_path)
        if venv_python:
            settings["plugins"]["jedi"] = {"environment": venv_python}
        await self._notify("workspace/didChangeConfiguration",
                           {"settings": {"pylsp": settings}})

        self._ready = True
        return True

    async def stop(self):
        proc = self._proc
        was_ready = self._ready
        self._ready = False
        if proc is None:
            self._fail_pending()
            return

        if was_ready and proc.returncode is None:
            try:
                await self._request("shutdown", None, timeout=2)
                await self._notify("exit", None)
            except Exception:
                pass

        if self._reader_task:
            self._reader_task.cancel()
            self._reader_task = None

        try:
            if proc.stdin:
                proc.stdin.close()
        except Exception:
            pass

        if proc.returncode is None:
            try:
                proc.terminate()
                await asyncio.wait_for(proc.wait(), timeout=1)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass

        self._proc = None
        self._uri = None
        self._fail_pending()

    async def did_open(self, path, text):
        if not self.alive:
            return
        self._uri = path_to_uri(path)
        self._version = 1
        await self._notify("textDocument/didOpen", {
            "textDocument": {
                "uri": self._uri,
                "languageId": self._language,
                "version": self._version,
                "text": text,
            },
        })

    async def did_change(self, text):
        if not self.running or not self._uri:
            return
        self._version += 1
        await self._notify("textDocument/didChange", {
            "textDocument": {"uri": self._uri, "version": self._version},
            "contentChanges": [{"text": text}],
        })

    async def did_close(self):
        if not self.running or not self._uri:
            return
        await self._notify("textDocument/didClose", {"textDocument": {"uri": self._uri}})
        self._uri = None

    async def complete(self, line, col):
        if not self.running or not self._uri:
            return []

        result = await self._request("textDocument/completion", {
            "textDocument": {"uri": self._uri},
            "position": {"line": line, "character": col},
        }, timeout=self.COMPLETE_TIMEOUT)

        if not result:
            return []
        items = result if isinstance(result, list) else result.get("items", [])
        items = sorted(items, key=lambda i: i.get("sortText") or i.get("label", ""))

        completions = []
        for item in items[:self.MAX_COMPLETIONS]:
            label = item.get("label", "")
            if not label:
                continue
            completions.append({
                "label": label,
                "insert": item.get("insertText") or label,
                "kind": item.get("kind"),
            })
        return completions

    async def _request(self, method, params, timeout=None):
        if not self.alive:
            return None
        self._id += 1
        rid = self._id
        future = self._loop.create_future()
        self._pending[rid] = future
        try:
            await self._send(self._message(method, params, rid))
            return await asyncio.wait_for(future, timeout or self.REQUEST_TIMEOUT)
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            print(f"[LSP] '{method}' failed: {e}")
            return None
        finally:
            self._pending.pop(rid, None)

    async def _notify(self, method, params):
        await self._send(self._message(method, params))

    @staticmethod
    def _message(method, params, rid=None):
        msg = {"jsonrpc": "2.0", "method": method}
        if rid is not None:
            msg["id"] = rid
        if params is not None:
            msg["params"] = params
        return msg

    async def _send(self, msg):
        proc = self._proc
        if proc is None or proc.returncode is not None or proc.stdin is None:
            return
        body = json.dumps(msg).encode("utf-8")
        header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
        try:
            proc.stdin.write(header + body)
            await proc.stdin.drain()
        except Exception as e:
            print(f"[LSP] Send error: {e}")

    async def _read_loop(self, proc):
        try:
            while True:
                length = 0
                while True:                       # headers
                    raw = await proc.stdout.readline()
                    if not raw:
                        return                    # server closed its output
                    line = raw.decode("ascii", "ignore").strip()
                    if not line:
                        break
                    name, _, value = line.partition(":")
                    if name.lower() == "content-length":
                        length = int(value.strip())
                if not length:
                    continue

                body = await proc.stdout.readexactly(length)
                try:
                    msg = json.loads(body)
                except ValueError:
                    continue
                await self._dispatch(msg)
        except (asyncio.IncompleteReadError, ConnectionError):
            pass
        except Exception as e:
            print(f"[LSP] Read loop error: {e}")
        finally:
            if proc is self._proc:
                self._ready = False
            self._fail_pending()

    async def _dispatch(self, msg):
        method = msg.get("method")
        rid = msg.get("id")

        if method is not None:
            if rid is not None:
                result = None
                if method == "workspace/configuration":
                    result = [None] * len(msg.get("params", {}).get("items", []))
                await self._send({"jsonrpc": "2.0", "id": rid, "result": result})
            return

        future = self._pending.get(rid)
        if future is None or future.done():
            return
        if "error" in msg:
            future.set_exception(Exception(msg["error"].get("message", "LSP error")))
        else:
            future.set_result(msg.get("result"))

    def _fail_pending(self):
        """Wake up everyone waiting on a reply that will never come."""
        for future in self._pending.values():
            if not future.done():
                future.set_result(None)
        self._pending.clear()