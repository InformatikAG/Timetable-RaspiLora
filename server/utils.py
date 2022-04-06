from typing import Any, Awaitable
from asyncio import get_event_loop
from functools import partial


def noblock(func, *args, **kwargs) -> Awaitable[Any]:
    return get_event_loop().run_in_executor(None, partial(func, *args, **kwargs))
