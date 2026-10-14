"""INTEGRATION: test the repository, pricing rules, and real SQLite together.

Syntax used in this file:
- pytest runs test_* functions. The store argument requests the fixture in
  conftest.py; pytest supplies a repository backed by a fresh temporary database.
- assert checks a condition. If false, Python raises AssertionError and pytest
  fails the case. == compares values; a dictionary comparison checks its contents.
- pytestmark labels all these tests "integration" so -m integration selects them.
- @ marks a decorator, which applies behavior or metadata to the next function.
  @pytest.mark.parametrize repeats a test for each listed quantity; each case
  receives fresh fixture setup and has its own pass/fail result.
- with pytest.raises(SomeError) expects that exception from the indented block.
  It fails if no exception or an unrelated one is raised. match= also checks the
  message against a regular expression, so we identify the intended failure.
- with store.connection() as connection opens a managed database connection.
  Leaving the block commits on success or rolls back on an exception, then closes
  it. A rollback undoes writes made in that transaction.
- SELECT COUNT(*) counts rows; fetchone() reads one result row and [0] reads its
  first column. list_products()[0] selects the first product (mug in ID order).
- ThreadPoolExecutor runs work on background threads. submit returns a Future,
  a handle to that work; result waits for its return value and propagates errors.
  Barrier(2) waits for both buyers before releasing them to attempt purchases.
  sorted(outcomes) lets us check results without assuming which buyer finishes first.
"""

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from app.repository import OutOfStock, ProductNotFound, Store

pytestmark = pytest.mark.integration


def test_order_and_stock_are_persisted(store):
    """WHY: returning an order is insufficient if it was never saved."""
    order = store.create_order("mug", 2)

    # A new repository object/connection proves the result lives on disk.
    reopened = Store(store.database_path)
    assert reopened.get_order(order["id"]) == order
    assert reopened.list_products()[0]["stock"] == 8
    assert order["total_cents"] == 3499


def test_restart_does_not_reset_inventory(store):
    """WHY: restarting the service must not refill sold inventory."""
    store.create_order("mug", 2)
    store.initialize()
    assert store.list_products()[0]["stock"] == 8


def test_unknown_product_creates_no_order(store):
    """WHY: a failed lookup must leave the database unchanged."""
    with pytest.raises(ProductNotFound):
        store.create_order("missing", 1)
    with store.connection() as connection:
        assert connection.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0
    assert store.list_products()[0]["stock"] == 10


def test_insufficient_stock_leaves_previous_order_intact(store):
    """WHY: rejecting a purchase must not partially reduce the remaining stock."""
    first_order = store.create_order("mug", 8)
    with pytest.raises(OutOfStock):
        store.create_order("mug", 3)
    assert store.list_products()[0]["stock"] == 2
    assert store.get_order(first_order["id"]) == first_order
    with store.connection() as connection:
        assert connection.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 1


def test_failed_insert_rolls_back_stock_reduction(store):
    """WHY: a database failure after reducing stock must undo that reduction."""
    # Deliberately inject a failure into real SQLite using a temporary test-only
    # trigger. This reaches a harder case than merely rejecting a request early:
    # the stock UPDATE succeeds, then the order INSERT fails.
    with store.connection() as connection:
        connection.executescript("""
            CREATE TRIGGER fail_order_insert BEFORE INSERT ON orders
            BEGIN
                SELECT RAISE(ABORT, 'simulated insert failure');
            END;
        """)

    with pytest.raises(sqlite3.IntegrityError, match="simulated insert failure"):
        store.create_order("mug", 2)

    # If someone removes the transaction, this assertion catches lost inventory.
    assert store.list_products()[0]["stock"] == 10
    with store.connection() as connection:
        assert connection.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0


def test_competing_orders_cannot_oversell(store):
    """WHY: two customers must not both buy the same remaining inventory."""
    ready = Barrier(2)

    def buy_eight_mugs():
        # Release both workers together, using independent database connections.
        ready.wait(timeout=5)
        try:
            store.create_order("mug", 8)
            return "created"
        except OutOfStock:
            return "out_of_stock"

    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = [pool.submit(buy_eight_mugs) for _ in range(2)]
        outcomes = [job.result(timeout=15) for job in jobs]

    # Which buyer wins does not matter. Exactly one must succeed.
    assert sorted(outcomes) == ["created", "out_of_stock"]
    assert store.list_products()[0]["stock"] == 2
    with store.connection() as connection:
        assert connection.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 1


@pytest.mark.parametrize("quantity", [0, 11, True, "2"])
def test_repository_rejects_invalid_quantities_without_http(store, quantity):
    """WHY: scripts using the repository must obey the same inventory limits."""
    with pytest.raises(ValueError, match="Quantity must be an integer"):
        store.create_order("mug", quantity)
    assert store.list_products()[0]["stock"] == 10
