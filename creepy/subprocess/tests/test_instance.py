import pytest

from creepy.subprocess import Pypen
from creepy.subprocess.instance import instantiate


def test_instantiate():
    process = Pypen('_detail/foo', serializable=True)
    inst = instantiate(process)
    assert inst.foo.__doc__ == "Foo."
    assert inst.bar.__doc__ == "Bar."
    result = inst.foo(10, "hello")
    assert result == (10, "hello", 1.5, (), False, {})
    result = inst.foo(20, "world", 3.0, "extra_arg", d=True, key1="value1")
    assert result == (20, "world", 3.0, ("extra_arg",), True, {'key1': 'value1'})
    with pytest.raises(TypeError):
        inst.foo(10)
    with pytest.raises(TypeError):
        inst.bar(10, 10, 10, 10)
