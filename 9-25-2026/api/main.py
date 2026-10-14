"""Start here: this file defines what the API accepts, calculates, and returns.

An API lets another program ask our code to do something over HTTP.
Here, a client sends a package's weight and shipping method, and our API
returns a price and delivery estimate. It does not save anything.

Run locally from the repo root:
    python -m uvicorn api.main:app --reload
Then open http://127.0.0.1:8000/docs to send a request from your browser.
"""

# Literal lets us restrict a value to a small list of allowed choices.
from typing import Literal

# FastAPI handles HTTP requests, calls our function, and produces HTTP responses.
from fastapi import FastAPI

# Mangum connects this same app to AWS Lambda. We use it at the bottom of the file.
from mangum import Mangum

# Pydantic models describe the data we expect and validate incoming values.
# Field adds rules, such as requiring a weight greater than zero.
from pydantic import BaseModel, Field

# This is the application object. The title and version appear in /docs.
# In the local command, "api.main:app" means "load app from api/main.py".
app = FastAPI(title="Shipping Quote API", version="1.0.0")


# REQUEST MODEL: the shape of the JSON a client sends to us.
# Both fields are required because neither has a default value.
class ShippingRequest(BaseModel):
    # float supports decimal weights, such as 1.5 kg.
    # gt=0 means greater than 0; le=100 means less than or equal to 100.
    # NaN and infinity are not valid package weights either.
    weight_kg: float = Field(gt=0, le=100, allow_inf_nan=False)

    # Only these two strings are allowed. "overnight" would be rejected.
    shipping_method: Literal["standard", "express"]


# RESPONSE MODEL: the shape of the JSON we promise to return.
# FastAPI also uses these field definitions to generate the API documentation.
class ShippingQuote(BaseModel):
    shipping_cost: float
    currency: str
    estimated_days: int


# A route connects an HTTP method and URL path to a Python function.
# POST is the method; /shipping-quote is the path.
# Example full local URL: http://127.0.0.1:8000/shipping-quote
#
# response_model tells FastAPI to validate and serialize the returned data
# using ShippingQuote. A successful call returns HTTP status 200 by default.
@app.post("/shipping-quote", response_model=ShippingQuote)
def shipping_quote(package: ShippingRequest):
    """Demo rates: $5 standard or $10 express, plus $2.50 per kg."""
    # FastAPI reads the request's JSON body and validates it with ShippingRequest
    # BEFORE calling this function. Invalid input produces a 422 response.
    # Valid input becomes an object, so we can use package.weight_kg, etc.

    # This comparison returns True for express shipping and False for standard.
    express = package.shipping_method == "express"

    # This is Python's short if/else expression: use $10 for express, otherwise $5.
    base_price = 10 if express else 5

    # These are fictional demo prices, not rates from a shipping carrier.
    # Example: 2 kg express = $10 base + (2 × $2.50) = $15.
    # FastAPI turns this Pydantic object into the JSON response sent to the client.
    return ShippingQuote(
        # Round the calculated price to two decimal places.
        shipping_cost=round(base_price + package.weight_kg * 2.5, 2),
        currency="USD",
        estimated_days=2 if express else 5,
    )


# AWS ENTRYPOINT: API Gateway passes the HTTP request to Lambda as an event.
# Mangum translates that event into a request FastAPI understands, then translates
# the response back into the format API Gateway needs.
#
# The CDK stack uses handler="main.handler" because the build script copies this
# file to main.py at the top of the Lambda package. Locally, Uvicorn uses app
# directly; it does not need this adapter.
#
# lifespan="off" disables startup/shutdown hooks in the adapter. This small app
# has no database connections or other resources that need those hooks.
handler = Mangum(app, lifespan="off")
