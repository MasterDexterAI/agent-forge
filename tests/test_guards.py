import pytest

from agentforge.core.guards import (
    GuardError,
    error_signature,
    hash_files,
    safe_path,
    validate_code_files,
)
from agentforge.core.schemas import FileWrite


@pytest.mark.parametrize("bad", ["../etc/passwd.py", "/abs/x.py", "a/../../b.py", "x.sh", ""])
def test_rejects_bad_paths(bad):
    with pytest.raises(GuardError):
        safe_path(bad)


@pytest.mark.parametrize("bad", ["tests/test_x.py", "conftest.py", "test_calc.py", ".git/hooks.py"])
def test_coder_cannot_write_protected_files(bad):
    with pytest.raises(GuardError):
        validate_code_files([FileWrite(path=bad, content="")])


def test_hash_is_order_independent():
    assert hash_files({"a.py": "1", "b.py": "2"}) == hash_files({"b.py": "2", "a.py": "1"})


def test_signature_ignores_numbers():
    assert error_signature("E   assert 5401 == 5400") == error_signature("E   assert 5399 == 5400")
