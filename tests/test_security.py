import pytest
from sovereign.security import safe_filename, validate_upload, safe_calculate

def test_filename_cannot_traverse():
    assert "/" not in safe_filename("../../hello world.pdf")
    assert safe_filename("../../hello world.pdf").endswith(".pdf")

def test_rejects_unsupported_extension():
    with pytest.raises(ValueError):
        validate_upload("evil.py", 100)

def test_calculator_basic():
    assert safe_calculate("(10 + 5) * 2") == 30

@pytest.mark.parametrize("expr", ["__import__('os').system('whoami')", "x+1", "open('/etc/passwd')", "2**99"])
def test_calculator_blocks_code(expr):
    with pytest.raises((ValueError, TypeError, SyntaxError)):
        safe_calculate(expr)
