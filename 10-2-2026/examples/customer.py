"""A tiny API client for the live demo; start Uvicorn before running this file."""

import httpx2 as httpx

# This is a manual demo, not an automated test. It prints what a customer sees.
with httpx.Client(base_url="http://127.0.0.1:8000", timeout=5) as customer:
    catalog = customer.get("/products")
    catalog.raise_for_status()
    print("Catalog:", catalog.json())

    response = customer.post("/orders", json={"product_id": "mug", "quantity": 2})
    response.raise_for_status()
    order = response.json()
    print("Created order:", order)

    saved = customer.get(f"/orders/{order['id']}")
    saved.raise_for_status()
    print("Saved order:", saved.json())
