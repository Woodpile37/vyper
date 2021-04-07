import pytest
from eth_tester.exceptions import TransactionFailed

from vyper import compiler
from vyper.exceptions import StateAccessViolation, SyntaxException


def test_variable_assignment(get_contract, keccak):
    code = """
@external
def foo() -> Bytes[4]:
    bar: Bytes[4] = slice(msg.data, 0, 4)
    return bar
"""

    contract = get_contract(code)

    assert contract.foo() == bytes(keccak(text="foo()")[:4])


def test_slicing_start_index_other_than_zero(get_contract):
    code = """
@external
def foo(_value: uint256) -> uint256:
    bar: Bytes[32] = slice(msg.data, 4, 32)
    return convert(bar, uint256)
"""

    contract = get_contract(code)

    assert contract.foo(42) == 42


def test_get_full_calldata(get_contract, keccak, w3):
    code = """
@external
def foo(bar: uint256) -> Bytes[36]:
    data: Bytes[36] = slice(msg.data, 0, 36)
    return data
"""
    contract = get_contract(code)

    # 2fbebd38000000000000000000000000000000000000000000000000000000000000002a
    method_id = keccak(text="foo(uint256)").hex()[2:10]  # 2fbebd38
    encoded_42 = w3.toBytes(42).hex()  # 2a
    expected_result = method_id + "00" * 31 + encoded_42

    assert contract.foo(42).hex() == expected_result


def test_get_len(get_contract):
    code = """
@external
def foo(bar: uint256) -> uint256:
    return len(msg.data)
"""
    contract = get_contract(code)

    assert contract.foo(42) == 36


fail_list = [
    """
@external
def foo() -> Bytes[4]:
    bar: Bytes[4] = msg.data
    return bar
    """,
    """
@external
def foo() -> Bytes[7]:
    bar: Bytes[7] = concat(msg.data, 0xc0ffee)
    return bar
    """,
    """
@external
def foo() -> uint256:
    bar: uint256 = convert(msg.data, uint256)
    return bar
    """,
    """
@internal
def foo() -> Bytes[4]:
    return slice(msg.data, 0, 4)
    """,
]

exceptions = [SyntaxException, SyntaxException, SyntaxException, StateAccessViolation]


@pytest.mark.parametrize(
    "bad_code,expected_error", zip(fail_list, exceptions),
)
def test_invalid_usages_compile_error(bad_code, expected_error):
    with pytest.raises(expected_error):
        compiler.compile_code(bad_code)


def test_runtime_failure_bounds_check(get_contract):
    code = """
@external
def foo(_value: uint256) -> uint256:
    val: Bytes[40] = slice(msg.data, 0, 40)
    return convert(slice(val, 4, 32), uint256)
"""

    contract = get_contract(code)

    with pytest.raises(TransactionFailed):
        contract.foo(42)
