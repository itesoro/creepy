import pytest

from creepy.subprocess import Pypen


def test_pypen_serialization():
    process = Pypen('_detail/process_with_state', serializable=True)
    initial_state = process.request('get_state')
    child_process = Pypen('_detail/state_modifier')
    modified_state = child_process.request('modify_and_get_state', process)
    state = process.request('get_state')
    assert state == modified_state
    assert state != initial_state


def test_pypen_serialization_error():
    process = Pypen('_detail/process_with_state', serializable=False)
    child_process = Pypen('_detail/state_modifier')
    with pytest.raises(RuntimeError):
        child_process.request('modify_and_get_state', process)


def test_proxy():
    process = Pypen('_detail/foo', serializable=True)
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
