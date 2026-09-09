"""Per-run event emitter.

The LangGraph nodes run inside a worker thread owned by ``main.py``. Nodes need
a way to push incremental output (streamed report tokens, progress) back to
that thread's queue without every node signature growing a callback argument.

A ContextVar gives us that: ``main.py`` installs an emitter at the top of the
worker thread, and any node can call ``emit(...)``. When no emitter is
installed -- unit tests, a direct graph invocation -- ``emit`` is a no-op.
"""
import contextvars
from typing import Callable, Optional

_emitter: contextvars.ContextVar[Optional[Callable[[str, dict], None]]] = (
    contextvars.ContextVar("research_emitter", default=None)
)


def set_emitter(fn: Optional[Callable[[str, dict], None]]) -> None:
    _emitter.set(fn)


def emit(event_type: str, data: dict) -> None:
    fn = _emitter.get()
    if fn is not None:
        fn(event_type, data)
