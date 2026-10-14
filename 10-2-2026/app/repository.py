"""SQLite persistence and the transaction that makes checkout safe.

An order and its stock reduction must succeed together. SQLite is a real disk
database, but ships with Python, so the demo needs no database server or Docker.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from app.pricing import calculate_totals


class ProductNotFound(Exception):
    """The requested product does not exist."""


class OutOfStock(Exception):
    """The product exists, but cannot satisfy this quantity."""


class Store:
    def __init__(self, database_path: Path):
        self.database_path = database_path

    @contextmanager
    def connection(self):
        # Each operation gets its own connection so request threads do not share
        # a SQLite connection. Explicitly close it after commit or rollback.
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize(self):
        """Create tables and seed a catalog without resetting existing stock."""
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS products (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    price_cents INTEGER NOT NULL CHECK (price_cents > 0),
                    stock INTEGER NOT NULL CHECK (stock >= 0)
                );
                CREATE TABLE IF NOT EXISTS orders (
                    id TEXT PRIMARY KEY,
                    product_id TEXT NOT NULL REFERENCES products(id),
                    quantity INTEGER NOT NULL CHECK (quantity BETWEEN 1 AND 10),
                    subtotal_cents INTEGER NOT NULL,
                    shipping_cents INTEGER NOT NULL,
                    total_cents INTEGER NOT NULL
                );
            """)
            connection.executemany(
                "INSERT OR IGNORE INTO products VALUES (?, ?, ?, ?)",
                [("mug", "Coffee mug", 1500, 10), ("notebook", "Notebook", 1000, 20)],
            )

    def list_products(self) -> list[dict]:
        with self.connection() as connection:
            rows = connection.execute("SELECT * FROM products ORDER BY id").fetchall()
            return [dict(row) for row in rows]

    def create_order(self, product_id: str, quantity: int) -> dict:
        # Enforce the invariant for callers that do not use HTTP, too.
        if type(quantity) is not int or not 1 <= quantity <= 10:
            raise ValueError("Quantity must be an integer between 1 and 10")

        with self.connection() as connection:
            # Acquire the write lock BEFORE reading stock. Two concurrent orders
            # cannot both buy the same remaining units from a stale stock count.
            connection.execute("BEGIN IMMEDIATE")
            product = connection.execute(
                "SELECT * FROM products WHERE id = ?", (product_id,)
            ).fetchone()
            if product is None:
                raise ProductNotFound(product_id)
            if quantity > product["stock"]:
                raise OutOfStock(product_id)

            # Prices come from our catalog, never from customer input.
            totals = calculate_totals(product["price_cents"], quantity)
            order = {
                "id": str(uuid4()),
                "product_id": product_id,
                "quantity": quantity,
                **totals,
            }
            connection.execute(
                "UPDATE products SET stock = stock - ? WHERE id = ?",
                (quantity, product_id),
            )
            # Named SQL parameters keep values out of SQL text and make the
            # mapping between the Python order and database columns visible.
            connection.execute("""
                INSERT INTO orders VALUES (
                    :id, :product_id, :quantity, :subtotal_cents,
                    :shipping_cents, :total_cents
                )
            """, order)
            # The connection context commits both writes together. An exception
            # during either write rolls back both, including the stock update.
            return order

    def get_order(self, order_id: str) -> dict | None:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT * FROM orders WHERE id = ?", (order_id,)
            ).fetchone()
            return dict(row) if row else None
