"""
tools/ - everything about tools, in one package.

    functions.py  - the plain tools (Python functions), their declarations (TOOLS), and fake order data
    hooks.py      - rules that run around every tool call (CCAF 1.5): PreToolUse and PostToolUse

Re-exported here so other files can simply write: from tools import TOOLS
"""

from tools.functions import ORDERS, TOOLS, declare

__all__ = ["ORDERS", "TOOLS", "declare"]
