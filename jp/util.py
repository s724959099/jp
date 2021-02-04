from contextlib import contextmanager
import asyncio
import inspect


def run_task(task):
    """
    Helper function to facilitate running a task in the async loop
    """
    loop = asyncio.get_event_loop()
    loop.create_task(task)


async def create_delayed_task(task, delay, loop):
    await asyncio.sleep(delay)
    loop.create_task(task)


def print_func_info(*args):
    # Calling function name
    print(inspect.stack()[1][3])
    for i in args:
        print(i)


@contextmanager
def try_save():
    try:
        yield
    except Exception:
        pass
