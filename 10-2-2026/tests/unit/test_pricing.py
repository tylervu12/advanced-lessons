"""UNIT TESTS: exercise one calculation without HTTP, files, or a database.

Syntax used in this file:
- pytest discovers functions whose names start with test_ and runs them for us.
- assert is a Python statement that checks whether an expression is true.
  If `assert result == expected` is false, it raises AssertionError and pytest
  marks that case as failed, showing the difference. == compares; = assigns.
- A decorator is the @ line above a function. It applies extra behavior or
  metadata to that function. @pytest.mark.parametrize tells pytest to run the
  function once for each supplied row of inputs, instead of writing many tests.
  The names in the string match function arguments; each tuple supplies values
  in that same order. ids supplies readable names for the resulting cases.
- pytestmark = pytest.mark.unit labels every test in this file as "unit".
  This lets `python -m pytest -m unit` select them; it does not run the tests.
- with pytest.raises(ValueError) checks that the indented code raises that
  exception. No exception, or an unrelated exception, fails the test. match=
  also checks the exception message against a regular expression (text pattern).
- Triple-quoted strings like this are docstrings: explanations, not assertions.

Arrange / Act / Assert describes the structure: prepare inputs, perform the
behavior, then compare the result with an independently chosen expectation.
"""

import pytest

from app.pricing import calculate_totals

# A marker labels tests; it does not change their behavior.
pytestmark = pytest.mark.unit


def test_small_order_includes_shipping():
    """WHY: undercharging shipping loses money on every small order."""
    # ARRANGE: two $15 mugs cost $30 before shipping.
    price, quantity = 1500, 2

    # ACT: call only the business rule being tested.
    result = calculate_totals(price, quantity)

    # ASSERT: literal expected amounts avoid copying the implementation's math
    # into the test and accidentally reproducing the same bug.
    assert result == {
        "subtotal_cents": 3000,
        "shipping_cents": 499,
        "total_cents": 3499,
    }


@pytest.mark.parametrize(
    "subtotal, expected_shipping, expected_total",
    [(4999, 499, 5498), (5000, 0, 5000), (5001, 0, 5001)],
    ids=["one-cent-below", "exactly-at-threshold", "one-cent-above"],
)
def test_free_shipping_boundary(subtotal, expected_shipping, expected_total):
    """WHY: >= accidentally becoming > would overcharge exactly-$50 orders."""
    # Parametrize runs this same test three times with readable case names.
    # One item lets us focus precisely on the free-shipping boundary.
    result = calculate_totals(subtotal, 1)
    assert result["shipping_cents"] == expected_shipping
    assert result["total_cents"] == expected_total


@pytest.mark.parametrize("price, quantity", [(0, 1), (-1, 1), (1500, 0), (1500, -1)])
def test_nonpositive_inputs_are_rejected(price, quantity):
    """WHY: direct Python callers must not create nonsensical totals."""
    # pytest.raises passes only when the block raises the expected exception.
    # A return value or an unrelated exception makes this test fail.
    with pytest.raises(ValueError, match="must be positive"):
        calculate_totals(price, quantity)
