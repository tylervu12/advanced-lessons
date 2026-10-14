"""INTEGRATION: HTTP contracts + validation + pricing + SQLite in one process.

These are integration tests even though requests look like HTTP. TestClient
does not test server startup in another process or real socket communication.

Syntax used in this file:
- pytest runs functions named test_*. The `client` argument requests a fixture
  from conftest.py: pytest creates the client and passes it into the function.
- assert checks that an expression is true. A false result raises AssertionError
  and fails the test. == means "equal to"; it does not assign a value.
- pytestmark labels every test here "integration" for `-m integration` selection.
- @ starts a decorator: a line that applies behavior or metadata to a function.
  @pytest.mark.parametrize runs the test once per listed quantity. pytest supplies
  quantity from that list and client from the fixture; they have different roles.
- client.post(..., json={...}) submits a JSON request body; client.get reads data.
  response.status_code is the HTTP outcome (201 created, 200 OK, 422 invalid
  input, 404 missing resource, 409 stock conflict). response.json() converts the
  JSON response text into Python dictionaries/lists for us to inspect.
- f"/orders/{order['id']}" is an f-string: it inserts the ID into the URL.
- isinstance(value, str) checks its type; `and value` also checks it is nonempty.
- any(...) is true if at least one item passes the check. In the validation test,
  the generator expression checks each error; ["loc"][-1] reads the last part of
  its field location, so we confirm the error is about quantity.
"""

import pytest

pytestmark = pytest.mark.integration


def test_create_and_read_order(client):
    """WHY: clients need the documented response and a retrievable order ID."""
    response = client.post("/orders", json={"product_id": "mug", "quantity": 2})
    assert response.status_code == 201
    order = response.json()
    assert order == {
        "id": order["id"],
        "product_id": "mug",
        "quantity": 2,
        "subtotal_cents": 3000,
        "shipping_cents": 499,
        "total_cents": 3499,
    }
    assert isinstance(order["id"], str) and order["id"]
    saved = client.get(f"/orders/{order['id']}")
    assert saved.status_code == 200
    assert saved.json() == order


@pytest.mark.parametrize("quantity", [0, -1, 11, 1.5, "2", True, None])
def test_invalid_quantity_returns_422_without_changing_stock(client, quantity):
    """WHY: malformed input must be rejected before inventory changes."""
    before = client.get("/products").json()
    response = client.post("/orders", json={"product_id": "mug", "quantity": quantity})
    assert response.status_code == 422
    # Check the field that failed, not Pydantic's full human-readable wording.
    assert any(error["loc"][-1] == "quantity" for error in response.json()["detail"])
    assert client.get("/products").json() == before


def test_customer_cannot_supply_the_price(client):
    """WHY: accepting a customer's price would allow one-cent purchases."""
    response = client.post(
        "/orders", json={"product_id": "mug", "quantity": 1, "price_cents": 1}
    )
    assert response.status_code == 422
    assert client.get("/products").json()[0]["stock"] == 10


def test_unknown_product_returns_404(client):
    """WHY: a missing product should produce a useful client error, not a 500."""
    response = client.post("/orders", json={"product_id": "missing", "quantity": 1})
    assert response.status_code == 404
    assert response.json() == {"detail": "Product not found"}


def test_sold_out_product_returns_409(client):
    """WHY: customers need to distinguish exhausted stock from bad input."""
    first = client.post("/orders", json={"product_id": "mug", "quantity": 10})
    assert first.status_code == 201
    response = client.post("/orders", json={"product_id": "mug", "quantity": 1})
    assert response.status_code == 409
    assert response.json() == {"detail": "Not enough stock"}
    assert client.get("/products").json()[0]["stock"] == 0


def test_unknown_order_returns_404(client):
    """WHY: a mistyped order ID should not look like a successful empty order."""
    response = client.get("/orders/does-not-exist")
    assert response.status_code == 404
    assert response.json() == {"detail": "Order not found"}
