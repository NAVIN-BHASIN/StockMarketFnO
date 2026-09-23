"""
Thread-Safe UI Callback Dispatcher for Tkinter & CustomTkinter.
----------------------------------------------------------------
Automatically prevents 'RuntimeError: main thread is not in main loop'
by intercepting any `widget.after(...)` calls made from background worker threads,
queuing them thread-safely, and executing them on the Tkinter main loop thread.
"""

import tkinter as tk
import threading
import queue

# Global thread-safe queue for UI tasks originating from background threads
_UI_QUEUE = queue.Queue()
_orig_after = tk.Misc.after
_orig_tk_init = tk.Tk.__init__
_pump_active = False


def _pump_ui(widget):
    """Drain and execute queued callbacks on the main UI thread."""
    global _pump_active
    while not _UI_QUEUE.empty():
        try:
            target, ms, func, args = _UI_QUEUE.get_nowait()
            try:
                if hasattr(target, "winfo_exists") and not target.winfo_exists():
                    continue
            except Exception:
                continue

            try:
                if ms == 0:
                    func(*args)
                else:
                    _orig_after(target, ms, func, *args)
            except Exception as e:
                func_name = getattr(func, "__name__", str(func))
                print(f"[UI Queue Dispatch Error in {func_name}]:", e)
        except queue.Empty:
            break

    try:
        if hasattr(widget, "winfo_exists") and widget.winfo_exists():
            _orig_after(widget, 25, lambda: _pump_ui(widget))
        else:
            _pump_active = False
    except Exception:
        _pump_active = False


def _safe_after(self, ms, func=None, *args):
    """
    Thread-safe drop-in replacement for tk.Misc.after.
    If called from the main thread, dispatches directly.
    If called from a background worker thread, enqueues to run safely on the main thread.
    """
    global _pump_active
    if func is None:
        return _orig_after(self, ms)

    if threading.current_thread() is threading.main_thread():
        if not _pump_active:
            _pump_active = True
            try:
                _orig_after(self, 25, lambda: _pump_ui(self))
            except Exception:
                _pump_active = False
        return _orig_after(self, ms, func, *args)
    else:
        # Worker thread: safely queue for main thread execution
        _UI_QUEUE.put((self, ms, func, args))
        return "queued_on_ui_thread"


def _safe_tk_init(self, *args, **kwargs):
    """Ensure UI pump is immediately bound and started on window creation."""
    _orig_tk_init(self, *args, **kwargs)
    global _pump_active
    if not _pump_active:
        _pump_active = True
        try:
            _orig_after(self, 25, lambda: _pump_ui(self))
        except Exception:
            _pump_active = False


# Install thread-safe hooks
if tk.Misc.after is not _safe_after:
    tk.Misc.after = _safe_after

if tk.Tk.__init__ is not _safe_tk_init:
    tk.Tk.__init__ = _safe_tk_init


def post_to_ui(widget, func, *args, delay_ms=0):
    """Helper function to explicitly schedule a function on the main UI thread."""
    if threading.current_thread() is threading.main_thread():
        if delay_ms == 0:
            try:
                func(*args)
            except Exception as e:
                print(f"[UI Dispatch Error]: {e}")
        else:
            _orig_after(widget, delay_ms, func, *args)
    else:
        _UI_QUEUE.put((widget, delay_ms, func, args))
