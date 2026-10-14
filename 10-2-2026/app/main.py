"""HTTP entrypoint. Run with: python -m uvicorn app.main:app --reload."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException

from app.models import Order, OrderRequest, Product
from app.repository import OutOfStock, ProductNotFound, Store


def create_app(database_path: Path | None = None) -> FastAPI:
    # The factory gives each test its own app/database. Normal startup uses a
    # local data file; the E2E server receives a temporary path through the env.
    store = Store(database_path or Path(os.getenv("STORE_DATABASE", "data/store.sqlite3")))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Importing this module does not create a database. Server startup does.
        store.initialize()
        yield

    app = FastAPI(title="Tiny Store — Testing Walkthrough", lifespan=lifespan)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/products", response_model=list[Product])
    def list_products():
        return store.list_products()

    @app.post("/orders", response_model=Order, status_code=201)
    def create_order(request: OrderRequest):
        try:
            return store.create_order(request.product_id, request.quantity)
        except ProductNotFound:
            raise HTTPException(status_code=404, detail="Product not found") from None
        except OutOfStock:
            # 409 means valid input conflicts with the store's current state.
            raise HTTPException(status_code=409, detail="Not enough stock") from None

    @app.get("/orders/{order_id}", response_model=Order)
    def get_order(order_id: str):
        order = store.get_order(order_id)
        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")
        return order

    return app


app = create_app()
