from contextlib import contextmanager


@contextmanager
def try_save():
    try:
        yield
    except Exception:
        pass
