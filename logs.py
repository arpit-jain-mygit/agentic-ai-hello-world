"""
logs.py - one tiny helper that prints every trace line.

Each line starts with WHERE it was printed from, as file:function,
so you can follow a run through the code, e.g.

    agent_loop.py:run_agent        | [order_agent] calls look_up_order(...)
"""

import inspect
import os
import re


def log(msg: str) -> None:
    """Print msg, tagged with the file and function that called log()."""
    caller = inspect.stack()[1]                                  # who called log()?
    where = f"{os.path.basename(caller.filename)}:{caller.function}"
    lines = msg.splitlines() or [""]
    # Lines 2+ of a multi-line message (e.g. a long answer) repeat line 1's indent and [agent] tag,
    # so you can still tell which agent said them.
    prefix = re.match(r"\s*(\[[^\]]+\] )?", lines[0]).group(0)
    print(f"{where:<30} | {lines[0]}")
    for line in lines[1:]:
        print(f"{where:<30} | {prefix}{line}")
