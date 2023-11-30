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
