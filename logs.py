"""
logs.py - one tiny helper that prints every trace line.

Each line starts with WHERE it was printed from, as file:function,
so you can follow a run through the code, e.g.

    loop.py:run_agent              | [order_agent] calls look_up_order(...)
"""

import inspect
import os


def log(msg: str) -> None:
    """Print msg, tagged with the file and function that called log()."""
    caller = inspect.stack()[1]                                  # who called log()?
    where = f"{os.path.basename(caller.filename)}:{caller.function}"
    for line in msg.splitlines():                                # tag every line, even multi-line answers
        print(f"{where:<30} | {line}")
