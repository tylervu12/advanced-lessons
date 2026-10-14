"""Call an existing AWS API; this script does not deploy anything."""

import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

if len(sys.argv) != 2:
    sys.exit("Usage: python examples/call_aws_api.py https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com")

# Pass the base URL printed by CDK as ApiUrl. Append the route we want to call.
url = sys.argv[1].rstrip("/") + "/shipping-quote"
payload = {"weight_kg": 2, "shipping_method": "express"}

# Equivalent to curl -X POST <url> -H 'Content-Type: application/json' -d '<json>'.
request = Request(
    url,
    method="POST",
    headers={"Content-Type": "application/json"},
    data=json.dumps(payload).encode("utf-8"),
)

try:
    with urlopen(request, timeout=30) as response:
        print(json.dumps(json.load(response), indent=2))
except HTTPError as exc:
    sys.exit(f"HTTP {exc.code}: {exc.read().decode('utf-8')}")
except URLError as exc:
    sys.exit(f"Could not reach the API: {exc.reason}")
