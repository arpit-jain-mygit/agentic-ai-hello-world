import inspect
import os
import re


def log(msg: str) -> None:
    caller = inspect.stack()[1]
    where = f"{os.path.basename(caller.filename)}:{caller.function}"
    lines = msg.splitlines() or [""]
    prefix = re.match(r"\s*(\[[^\]]+\] )?", lines[0]).group(0)
    print(f"{where:<30} | {lines[0]}")
    for line in lines[1:]:
        print(f"{where:<30} | {prefix}{line}")
