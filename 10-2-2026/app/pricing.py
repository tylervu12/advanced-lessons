"""Business rules, deliberately independent of FastAPI and SQLite.

Keeping calculations here lets unit tests explain a rule without setting up a
server or database. Money is stored as integer cents to avoid floating point
rounding surprises (for example, 0.1 + 0.2).
"""

FREE_SHIPPING_MINIMUM_CENTS = 5000
SHIPPING_FEE_CENTS = 499


def calculate_totals(unit_price_cents: int, quantity: int) -> dict[str, int]:
    """Orders of $50 or more ship free; smaller orders pay $4.99 shipping."""
    # Validate here as well as at the HTTP boundary: another Python caller could
    # use this function without ever going through the API's request validation.
    if unit_price_cents <= 0:
        raise ValueError("Unit price must be positive")
    if quantity <= 0:
        raise ValueError("Quantity must be positive")

    subtotal = unit_price_cents * quantity
    shipping = 0 if subtotal >= FREE_SHIPPING_MINIMUM_CENTS else SHIPPING_FEE_CENTS
    return {
        "subtotal_cents": subtotal,
        "shipping_cents": shipping,
        "total_cents": subtotal + shipping,
    }
