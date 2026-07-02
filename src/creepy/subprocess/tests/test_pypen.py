import fcntl

import pytest

from creepy.subprocess import Pypen


def test_pypen_serialization():
    with Pypen('_detail/process_with_state', serializable=True) as process, \
            Pypen('_detail/state_modifier') as child_process:
        initial_state = process.request('get_state')
        modified_state = child_process.request('modify_and_get_state', process)
        state = process.request('get_state')
    assert state == modified_state
    assert state != initial_state


def test_pypen_serialization_error():
    with Pypen('_detail/process_with_state', serializable=False) as process, \
            Pypen('_detail/state_modifier') as child_process:
        with pytest.raises(RuntimeError):
            child_process.request('modify_and_get_state', process)


def test_compile():
    with Pypen('_detail/foo', serializable=True) as process:
        instance = process.compile()
        assert instance.foo.__doc__ == "Foo."
        assert instance.bar.__doc__ == "Bar."
        result = instance.foo(10, "hello")
        assert result == (10, "hello", 1.5, (), False, {})
        result = instance.foo(20, "world", 3.0, "extra_arg", d=True, key1="value1")
        assert result == (20, "world", 3.0, ("extra_arg",), True, {'key1': 'value1'})
        with pytest.raises(TypeError):
            instance.foo(10)
        with pytest.raises(TypeError):
            instance.bar(10, 10, 10, 10)


def test_inline_code_execution():
    code = """
from creepy.subprocess import App
app = App()
@app.route('add')
def add(a, b):
    return a + b
app.run()
""".strip()
    with Pypen(['-c', code]) as process:
        assert process.request('add', 2, 3) == 5


def test_large_message_execution():
    code = """
from creepy.subprocess import App
app = App()
@app.route('echo')
def echo(value):
    return value
app.run()
""".strip()
    with Pypen(['-c', code]) as process:
        message = b'x' * 60_000
        pipe_capacity = min(fcntl.fcntl(process._fds[1], fcntl.F_GETPIPE_SZ),
                            fcntl.fcntl(process._fds[2], fcntl.F_GETPIPE_SZ))
        assert pipe_capacity >= len(message)
        assert process.request('echo', message) == message
