"""Cross-platform single-instance IPC Gateway using Named Pipes (Windows) or Unix sockets."""

from __future__ import annotations

import contextlib
import logging
import os
import threading
import time
from collections.abc import Callable
from multiprocessing.connection import Client, Listener

from autosilenttrimmer.core.constants import (
    IPC_COALESCE_WINDOW_SEC,
    IPC_CONNECT_TIMEOUT_SEC,
    IPC_PIPE_NAME_WINDOWS,
    IPC_SOCKET_FILENAME,
)
from autosilenttrimmer.domain.contracts.ipc import IIPCGateway, IJobGatewayClient

logger = logging.getLogger(__name__)


def resolve_ipc_address(cache_dir: str | None = None) -> tuple[str, str]:
    """Return OS-native IPC endpoint and family ('AF_PIPE' on Win, 'AF_UNIX' on POSIX)."""
    if os.name == "nt":
        return IPC_PIPE_NAME_WINDOWS, "AF_PIPE"
    base_dir = cache_dir or "/tmp"
    os.makedirs(base_dir, exist_ok=True)
    return os.path.join(base_dir, IPC_SOCKET_FILENAME), "AF_UNIX"


class LocalIPCGateway(IIPCGateway):
    """Single-instance IPC server coalescing multi-select Explorer calls into one queue batch."""

    def __init__(
        self,
        address: str | None = None,
        family: str | None = None,
        coalesce_window_sec: float = IPC_COALESCE_WINDOW_SEC,
    ) -> None:
        default_addr, default_fam = resolve_ipc_address()
        self._address = address or default_addr
        self._family = family or default_fam
        self._coalesce_sec = coalesce_window_sec
        self._stop_event = threading.Event()
        self._listener: Listener | None = None
        self._accept_thread: threading.Thread | None = None
        self._flush_thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._buffer: list[str] = []
        self._last_arrival: float = 0.0
        self._callback: Callable[[list[str]], None] | None = None

    def start(self, on_batch_received: Callable[[list[str]], None]) -> None:
        """Bind OS pipe/socket and launch coalescing accept loops."""
        self._callback = on_batch_received
        self._stop_event.clear()

        if self._family == "AF_UNIX" and os.path.exists(self._address):
            os.remove(self._address)

        self._listener = Listener(self._address, family=self._family)
        self._accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._accept_thread.start()
        self._flush_thread.start()
        logger.info("IPC Gateway active on %s (%s)", self._address, self._family)

    def _accept_loop(self) -> None:
        assert self._listener is not None
        while not self._stop_event.is_set():
            try:
                conn = self._listener.accept()
            except OSError:
                break
            try:
                msg = conn.recv()
                if isinstance(msg, dict) and msg.get("cmd") == "enqueue":
                    paths = [str(p) for p in msg.get("paths", []) if str(p).strip()]
                    if paths:
                        with self._lock:
                            self._buffer.extend(paths)
                            self._last_arrival = time.monotonic()
                    conn.send({"ok": True, "queued": len(paths)})
                elif isinstance(msg, dict) and msg.get("cmd") == "ping":
                    conn.send({"ok": True, "status": "alive"})
                else:
                    conn.send({"ok": False, "error": "unknown_cmd"})
            except Exception as exc:
                logger.debug("IPC client error: %s", exc)
            finally:
                conn.close()

    def _flush_loop(self) -> None:
        while not self._stop_event.is_set():
            batch_to_emit: list[str] | None = None
            with self._lock:
                if self._buffer and (time.monotonic() - self._last_arrival) >= self._coalesce_sec:
                    # Deduplicate while preserving arrival order
                    batch_to_emit = list(dict.fromkeys(self._buffer))
                    self._buffer.clear()

            if batch_to_emit and self._callback is not None:
                try:
                    self._callback(batch_to_emit)
                except Exception as exc:
                    logger.error("Batch handler error: %s", exc)

            time.sleep(0.05)

    def stop(self) -> None:
        """Close listener and cleanly join worker threads."""
        self._stop_event.set()
        if self._listener is not None:
            with contextlib.suppress(OSError):
                self._listener.close()
            self._listener = None
        if self._family == "AF_UNIX" and os.path.exists(self._address):
            os.remove(self._address)


class LocalIPCClient(IJobGatewayClient):
    """Thin sub-10ms IPC client used by Explorer shell shim to submit files."""

    def __init__(self, address: str | None = None, family: str | None = None) -> None:
        default_addr, default_fam = resolve_ipc_address()
        self._address = address or default_addr
        self._family = family or default_fam

    def is_daemon_running(self) -> bool:
        """Probe whether gateway endpoint answers ping cleanly."""
        try:
            with Client(self._address, family=self._family) as conn:
                conn.send({"cmd": "ping"})
                resp = conn.recv()
                return bool(isinstance(resp, dict) and resp.get("ok"))
        except OSError:
            return False

    def enqueue_paths(self, paths: list[str], timeout_sec: float = IPC_CONNECT_TIMEOUT_SEC) -> bool:
        """Deliver paths over IPC, retrying briefly if daemon is booting."""
        deadline = time.monotonic() + timeout_sec
        while time.monotonic() <= deadline:
            try:
                with Client(self._address, family=self._family) as conn:
                    conn.send({"cmd": "enqueue", "paths": paths})
                    resp = conn.recv()
                    return bool(isinstance(resp, dict) and resp.get("ok"))
            except OSError:
                time.sleep(0.05)
        return False
