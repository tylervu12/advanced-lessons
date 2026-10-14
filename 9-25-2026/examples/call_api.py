"""Read second: this is the client, a separate program that calls the API.

Local: python examples/call_api.py
AWS:   python examples/call_api.py https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com

This script uses Python's standard library. It does not import the pricing
function: it sends an HTTP request, just as another application would.
"""

# json converts between Python values and the JSON format used over HTTP.
# sys gives us command-line arguments, error output, and an exit status.
import json
import sys

# urllib provides an HTTP client without installing an extra library.
from urllib.error import HTTPError
from urllib.request import Request, urlopen

# sys.argv[0] is the script name. sys.argv[1], if present, is the URL you supplied.
# With no URL argument, call the local server. Start Uvicorn before running this.
base_url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"

# This Python dictionary matches ShippingRequest in api/main.py.
# Change these values to try another quote or trigger a validation error.
payload = {"weight_kg": 2, "shipping_method": "express"}

# Build a request. Creating this object alone does NOT send anything yet.
request = Request(
    # Remove a trailing slash so the base URL and route join cleanly.
    f"{base_url.rstrip('/')}/shipping-quote",

    # Convert the dictionary to JSON text, then encode that text as bytes.
    data=json.dumps(payload).encode(),

    # A header describes the request. This one tells the server the body is JSON.
    headers={"Content-Type": "application/json"},
    method="POST",
)

try:
    # This is where the network call happens. Wait up to 30 seconds for network
    # operations instead of waiting indefinitely. "with" closes the response.
    with urlopen(request, timeout=30) as response:
        # Read the JSON response into Python, then print it in an easy-to-read form.
        print(json.dumps(json.load(response), indent=2))
except HTTPError as exc:
    # A response such as 422 means the server received the request but rejected it.
    # Print both its HTTP status and response body so the caller can see why.
    # Connection failures (for example, Uvicorn not running) are different errors
    # and are not caught by this HTTPError block.
    print(f"HTTP {exc.code}: {exc.read().decode()}", file=sys.stderr)

    # A nonzero exit status tells the terminal or another script that this failed.
    sys.exit(1)
