"""E2E: a customer's complete API journey over actual local HTTP.

Nothing in these tests imports application code or directly queries SQLite.
Observations go through the public API, just like an external API client.
This project's product is an API, so its end-to-end boundary has no browser UI.

Syntax used in this file:
- pytest discovers and runs functions named test_*. pytestmark labels all of
  them "e2e", so `python -m pytest -m e2e` selects this group.
- running_server is a fixture argument supplied by pytest from conftest.py.
  Its value is a function. Calling it creates a context manager used with `with`.
- with running_server() as customer starts the server and provides an HTTP
  client. Leaving the block stops the server, including when an assertion fails.
  Calling it again in the same test restarts with the same saved database.
- assert checks a condition; if false, AssertionError makes pytest fail the
  test. == compares values. Assertions check responses, not just whether a call
  completed: a request returning an error is still a completed HTTP request.
- .get reads a URL; .post(..., json={...}) submits JSON. .status_code contains
  the HTTP result: 200 OK, 201 created, or 409 conflict for insufficient stock.
  .json() converts the response body into Python dictionaries/lists.
- next(product for product in ... if ...) finds the first matching product.
  [0] selects the first list item; ["stock"] selects a dictionary field.
- An f-string, such as f"/orders/{order['id']}", inserts a value into a string.
"""

import pytest

pytestmark = pytest.mark.e2e


def test_customer_buys_mugs_and_order_survives_restart(running_server):
    """WHY: checkout must work through the deployed entrypoint and survive exit."""
    with running_server() as customer:
        # ARRANGE: discover a product through the catalog, as a customer would.
        catalog = customer.get("/products")
        assert catalog.status_code == 200
        mug = next(product for product in catalog.json() if product["id"] == "mug")
        assert mug["stock"] == 10

        # ACT: buy two mugs via a real TCP socket and server process.
        response = customer.post("/orders", json={"product_id": mug["id"], "quantity": 2})
        assert response.status_code == 201
        order = response.json()

        # ASSERT: the customer sees the right charge and reduced inventory.
        assert order["total_cents"] == 3499
        assert order["quantity"] == 2
        assert order["product_id"] == "mug"
        assert customer.get("/products").json()[0]["stock"] == 8

    # The first process has exited. A NEW process must recover the saved order
    # from SQLite; returning an in-memory object would fail this check.
    with running_server() as returning_customer:
        saved = returning_customer.get(f"/orders/{order['id']}")
        assert saved.status_code == 200
        assert saved.json() == order
        assert returning_customer.get("/products").json()[0]["stock"] == 8


def test_customer_receives_free_shipping_at_fifty_dollars(running_server):
    """WHY: the unit-tested discount must actually reach the public response."""
    with running_server() as customer:
        response = customer.post("/orders", json={"product_id": "notebook", "quantity": 5})
        assert response.status_code == 201
        order = response.json()
        assert order["subtotal_cents"] == 5000
        assert order["shipping_cents"] == 0
        assert order["total_cents"] == 5000
        assert customer.get(f"/orders/{order['id']}").json() == order


def test_customer_cannot_buy_a_sold_out_product(running_server):
    """WHY: the complete system must protect inventory and explain rejection."""
    with running_server() as customer:
        # One customer buys all the mugs before a second purchase is attempted.
        first = customer.post("/orders", json={"product_id": "mug", "quantity": 10})
        assert first.status_code == 201
        rejected = customer.post("/orders", json={"product_id": "mug", "quantity": 1})
        assert rejected.status_code == 409
        assert rejected.json() == {"detail": "Not enough stock"}
        assert customer.get("/products").json()[0]["stock"] == 0
        # A rejected purchase must not damage the successful customer's order.
        assert customer.get(f"/orders/{first.json()['id']}").json() == first.json()
