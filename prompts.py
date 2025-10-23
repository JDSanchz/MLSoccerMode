"""
Input helper utilities that can be redirected to different front-ends.

The module defaults to CLI input, but callers can register a custom handler
to plug into alternative interfaces such as Streamlit.  The handler receives
the same arguments as `prompt_int` and must raise `ValueError` if a value is
invalid so the retry loop can continue.
"""

from typing import Callable, Optional

PromptIntHandler = Callable[[str, int, int], int]
_prompt_int_handler: Optional[PromptIntHandler] = None


def set_prompt_int_handler(handler: Optional[PromptIntHandler]) -> None:
    """Register a custom handler for integer prompts."""
    global _prompt_int_handler
    _prompt_int_handler = handler


def prompt_int(msg, lo, hi):
    if _prompt_int_handler is not None:
        return _prompt_int_handler(msg, lo, hi)

    while True:
        try:
            v = int(input(msg))
            if lo <= v <= hi:
                return v
        except Exception:
            pass
        print(f"Enter a number between {lo} and {hi}.")
