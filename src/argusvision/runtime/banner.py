"""Terminal branding for ArgusVision runs.

A run that takes hours should say what it is doing, on what hardware, against
which data, from the first second. The banner is also the only place a user
sees the resolved configuration before the GPU starts working — a wrong
weights path or a wrong split costs hours if it surfaces at the end instead.

Colour follows the logo: ARGUS in grey, VISION in magenta. It is dropped
automatically when stdout is not a terminal, when `NO_COLOR` is set, or on a
Windows console that refuses ANSI — a log file full of escape codes is worse
than no colour.
"""

import os
import shutil
import sys
from typing import Dict, Iterable, Optional, Tuple

__all__ = ["print_banner", "print_section", "print_kv", "supports_colour", "C"]

_ESC = "\033["


class _Palette:
    """ANSI codes, blanked out when the terminal cannot render them."""

    def __init__(self, enabled: bool):
        self.enabled = enabled
        self.reset = f"{_ESC}0m" if enabled else ""
        self.bold = f"{_ESC}1m" if enabled else ""
        self.dim = f"{_ESC}2m" if enabled else ""
        self.grey = f"{_ESC}38;5;250m" if enabled else ""
        self.dark = f"{_ESC}38;5;240m" if enabled else ""
        self.magenta = f"{_ESC}38;5;201m" if enabled else ""
        self.cyan = f"{_ESC}38;5;51m" if enabled else ""
        self.green = f"{_ESC}38;5;46m" if enabled else ""
        self.red = f"{_ESC}38;5;196m" if enabled else ""
        self.yellow = f"{_ESC}38;5;220m" if enabled else ""


def supports_colour(stream=None) -> bool:
    stream = stream or sys.stdout
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    if not hasattr(stream, "isatty") or not stream.isatty():
        return False
    if sys.platform == "win32":
        # Windows 10+ terminals handle ANSI once virtual-terminal mode is on;
        # enabling it is cheap and failing is harmless.
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            return False
    return True


C = _Palette(supports_colour())


def _enable_unicode(stream=None) -> bool:
    """Try to put the stream into UTF-8, and report whether box glyphs are safe.

    Windows consoles frequently default to a legacy code page (cp1253 here),
    which cannot encode box-drawing characters — printing them raises
    UnicodeEncodeError and kills the run before inference starts. Reconfigure
    where possible, and otherwise fall back to ASCII rather than crash.
    """
    stream = stream or sys.stdout
    encoding = (getattr(stream, "encoding", None) or "").lower()
    if "utf" in encoding:
        return True
    reconfigure = getattr(stream, "reconfigure", None)
    if callable(reconfigure):
        try:
            reconfigure(encoding="utf-8", errors="replace")
            return True
        except Exception:
            pass
    try:
        "─█▄▀".encode(encoding or "ascii")
        return True
    except (UnicodeEncodeError, LookupError):
        return False


UNICODE = _enable_unicode()

# Glyphs degrade to ASCII on a console that cannot encode them.
_G = {
    "rule": "─" if UNICODE else "-",
    "bar_full": "█" if UNICODE else "#",
    "bar_empty": "░" if UNICODE else ".",
    "arrow": "→" if UNICODE else "->",
    "mid": "·" if UNICODE else "-",
    "ok": "✓" if UNICODE else "+",
    "fail": "✗" if UNICODE else "x",
}


def glyph(name: str) -> str:
    return _G.get(name, "")


def _width(default: int = 78) -> int:
    try:
        return max(60, min(shutil.get_terminal_size().columns - 2, 100))
    except Exception:
        return default


# The interlocked A/V of the logo mark, reduced to two rows of half-blocks so
# it survives any monospace font — with a plain-ASCII twin for legacy consoles.
_MARK = (
    ("▄▀█ █░█", "█▀█ ▀▄▀")
    if UNICODE
    else ("/\\ \\  /", "/--\\ \\/")
)


def print_banner(
    title: str = "",
    subtitle: str = "",
    fields: Optional[Dict[str, object]] = None,
    version: Optional[str] = None,
) -> None:
    """Print the ArgusVision mark, wordmark, and the resolved run context."""
    if version is None:
        try:
            from argusvision import __version__ as version  # type: ignore
        except Exception:
            version = "0.1.0"

    w = _width()
    line = _G["rule"] * w

    print()
    print(f"{C.dark}{line}{C.reset}")
    print(
        f"  {C.grey}{C.bold}{_MARK[0]}{C.reset}    "
        f"{C.grey}{C.bold}ARGUS{C.reset}{C.magenta}{C.bold}VISION{C.reset}"
    )
    print(
        f"  {C.magenta}{C.bold}{_MARK[1]}{C.reset}    "
        f"{C.dim}aerial detection {_G['arrow']} segmentation platform "
        f"{_G['mid']} v{version}{C.reset}"
    )
    print(f"{C.dark}{line}{C.reset}")

    if title:
        print(f"  {C.bold}{title}{C.reset}")
    if subtitle:
        print(f"  {C.dim}{subtitle}{C.reset}")
    if title or subtitle:
        print(f"{C.dark}{line}{C.reset}")

    if fields:
        print_kv(fields)
        print(f"{C.dark}{line}{C.reset}")
    print()


def print_kv(fields: Dict[str, object], indent: str = "  ") -> None:
    """Aligned key/value block — the resolved context, one fact per line."""
    if not fields:
        return
    pad = max(len(str(k)) for k in fields)
    for key, value in fields.items():
        print(f"{indent}{C.dim}{str(key):<{pad}}{C.reset}  {value}")


def print_section(text: str, char: str = "") -> None:
    char = char or _G["rule"]
    w = _width()
    print()
    print(f"{C.magenta}{char * w}{C.reset}")
    print(f"  {C.bold}{text}{C.reset}")
    print(f"{C.magenta}{char * w}{C.reset}")
    print()


def print_result_table(
    headers: Iterable[str], rows: Iterable[Iterable[object]]
) -> None:
    """Minimal aligned table for end-of-run metrics."""
    headers = [str(h) for h in headers]
    body = [[str(c) for c in row] for row in rows]
    widths = [
        max(len(headers[i]), max((len(r[i]) for r in body), default=0))
        for i in range(len(headers))
    ]
    head = "  ".join(f"{C.bold}{h:<{widths[i]}}{C.reset}" for i, h in enumerate(headers))
    print(f"  {head}")
    print(f"  {C.dark}{'  '.join(_G['rule'] * x for x in widths)}{C.reset}")
    for row in body:
        print("  " + "  ".join(f"{c:<{widths[i]}}" for i, c in enumerate(row)))
    print()


def print_status(state: str, message: str) -> None:
    colour = {
        "ok": C.green,
        "done": C.green,
        "warn": C.yellow,
        "fail": C.red,
        "info": C.cyan,
    }.get(state, C.cyan)
    marker = {
        "ok": _G["ok"],
        "done": _G["ok"],
        "warn": "!",
        "fail": _G["fail"],
        "info": _G["mid"],
    }.get(state, _G["mid"])
    print(f"  {colour}{marker}{C.reset} {message}")
