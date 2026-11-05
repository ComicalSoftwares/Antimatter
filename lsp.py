import asyncio
import json
import os
import threading
from pathlib import Path

import util

LANG_SERVERS = {
    "python": [util.python_exe(), "-m", "pylsp"]
}

_loop = None
_loop_lock = threading.Lock()


def get_loop():
    global _loop
    with _loop_lock:
        if _loop is None:
            _loop = asyncio.new_event_loop()
            threading.Thread(target=_loop.run_forever, daemon=True, name="antimatter-lsp").start()
        return _loop


def register_server(language, command):
    LANG_SERVERS[language] = list(command)


def path_to_uri(path):
    return Path(os.path.abspath(path)).as_uri()


class LspClient:

    def __init__(self):
        self._proc = None
        self._id = 0
        self._pending = {}
        self._reader_task = None
        self._version = 0
        self._uri = None
        self._language = None
        self._loop = None

    @property
    def running(self):
        return self._proc is not None and self._proc.returncode is None

    @property
    def uri(self):
        return self._uri

    async def start(self, language, root_path):
        cmd = LANG_SERVERS.get(language)
        if not cmd:
            return False
        self._loop = asyncio.get_running_loop()

        try:
            self._proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
        except Exception as e:
            print(f"[LSP Error] Failed to launch server binary: {e}")
            self._proc = None
            return False

        self._reader_task = self._loop.create_task(self._read_loop())
        self._language = language

        init_res = await self._request("initialize", {
            "processId": os.getpid(),
            "rootUri": path_to_uri(root_path),
            "capabilities": {
                "textDocument": {
                    "completion": {
                        "completionItem": {"snippetSupport": False},
                    },
                },
            },
        }, timeout=20)

        if init_res is None:
            print("[LSP Error] Initialize request failed or timed out.")
            await self.stop()
            return False

        await self._notify("initialized", {})
        return True

    async def stop(self):
        if self._proc is None:
            return

        if self.running:
            try:
                await asyncio.wait_for(self._request("shutdown", None), timeout=2)
                await self._notify("exit", None)
            except Exception:
                pass

        if self._reader_task:
            self._reader_task.cancel()
            self._reader_task = None
        if self._proc:
            try:
                if self._proc.stdin:
                    self._proc.stdin.close()
            except Exception:
                pass
            try:
                if self._proc.returncode is None:
                    self._proc.terminate()
                    await asyncio.wait_for(self._proc.wait(), timeout=1)
            except Exception:
                try:
                    self._proc.kill()
                except Exception:
                    pass
        self._proc = None
        self._uri = None
        self._fail_pending()

    async def did_open(self, path, text):
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

    async def did_close(self):
        if not self._uri:
            return
        uri, self._uri = self._uri, None
        await self._notify("textDocument/didClose", {"textDocument": {"uri": uri}})

    async def did_change(self, text):
        if not self._uri:
            return
        self._version += 1
        await self._notify("textDocument/didChange", {
            "textDocument": {"uri": self._uri, "version": self._version},
            "contentChanges": [{"text": text}],
        })

    async def complete(self, line, col):
        if not self._uri or not self.running:
            return []

        try:
            result = await asyncio.wait_for(
                self._request("textDocument/completion", {
                    "textDocument": {"uri": self._uri},
                    "position": {"line": line, "character": col},
                }),
                timeout=5,
            )
        except Exception as e:
            print(f"[LSP Error] Completion request exception: {e}")
            return []

        if not result:
            return []

        items = result if isinstance(result, list) else result.get("items", [])
        items = sorted(items, key=lambda i: i.get("sortText") or i.get("label", ""))

        completions = []
        seen = set()
        for item in items:
            label = item.get("label", "")
            if not label or label in seen:
                continue
            seen.add(label)
            text_edit = item.get("textEdit")
            insert = item.get("insertText") or (text_edit or {}).get("newText") or label
            completions.append({"label": label, "insert": insert})
            if len(completions) >= 200:
                break

        return completions

    def _fail_pending(self):
        pending, self._pending = self._pending, {}
        for future in pending.values():
            if not future.done():
                future.set_result(None)

    async def _request(self, method, params, timeout=5):
        self._id += 1
        rid = self._id

        future = self._loop.create_future()
        self._pending[rid] = future

        await self._send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self._pending.pop(rid, None)
            return None
        except Exception:
            self._pending.pop(rid, None)
            return None

    async def _notify(self, method, params):
        await self._send({"jsonrpc": "2.0", "method": method, "params": params})

    async def _send(self, msg):
        if not self.running or not self._proc.stdin:
            return
        body = json.dumps(msg).encode("utf-8")
        header = f"Content-Length: {len(body)}\r\n\r\n".encode("latin1")
        try:
            self._proc.stdin.write(header + body)
            await self._proc.stdin.drain()
        except Exception as e:
            print(f"[LSP Send Error]: {e}")

    async def _read_loop(self):
        try:
            while True:
                content_length = 0
                while True:
                    line_bytes = await self._proc.stdout.readline()
                    if not line_bytes:
                        return
                    line = line_bytes.decode("latin1").strip("\r\n")
                    if not line:
                        break
                    if line.lower().startswith("content-length:"):
                        content_length = int(line.split(":")[1].strip())

                if content_length == 0:
                    continue

                body = await self._proc.stdout.readexactly(content_length)
                msg = json.loads(body.decode("utf-8"))

                rid = msg.get("id")
                if "method" in msg:
                    if rid is not None:
                        await self._send({"jsonrpc": "2.0", "id": rid, "result": None})
                    continue

                if rid is not None and rid in self._pending:
                    future = self._pending.pop(rid)
                    if not future.done():
                        result = msg.get("result")
                        future.set_result(None if "error" in msg else ({} if result is None else result))
        except (asyncio.CancelledError, ConnectionError, asyncio.IncompleteReadError):
            pass
        except Exception as e:
            print(f"[LSP Read Loop Error]: {e}")
        finally:
            self._fail_pending()
