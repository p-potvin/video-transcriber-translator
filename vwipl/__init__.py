"""
vwipl (VaultWares Inline Progress Logger)
A reusable library for generating text-based progress bars and spinners
with support for both CLI \r rendering and GUI text replacement flags.
"""

from .progress import IndeterminateBar, DeterminateBar, Spinner

__all__ = ["IndeterminateBar", "DeterminateBar", "Spinner"]
