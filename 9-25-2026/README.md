# Shipping Quote API

One FastAPI endpoint, deployed to AWS Lambda and API Gateway using CDK.

## Start here if APIs are new to you

An **API** lets one program ask another program to do something. In this demo, a client asks for a shipping quote. The server calculates it and sends back a response. Nothing is saved, and no shipping carrier is contacted.

An HTTP request has a few pieces:

| Piece | In this demo | What it means |
| --- | --- | --- |
| Base URL | `http://127.0.0.1:8000` locally | Where the server is running; `127.0.0.1` is your own computer |
| Path | `/shipping-quote` | Which operation to call |
| Method | `POST` | Send input to this operation in a request body |
| Header | `Content-Type: application/json` | Tell the server the body contains JSON |
| Body | `{"weight_kg": 2, "shipping_method": "express"}` | The input data |

The **endpoint** is the method and path together: `POST /shipping-quote`. The full local URL is `http://127.0.0.1:8000/shipping-quote`.

**JSON** is a text format for structured data. It looks similar to a Python dictionary, but it travels over the network as text. The server returns JSON containing the price, currency, and estimated delivery days, along with an **HTTP status code**: `200` for a successful quote or `422` when the input fails validation.

Opening the quote URL in a browser's address bar sends a `GET`, so it will not call our `POST` endpoint. Instead, open `/docs` and use **Try it out**, or run the Python caller. The `/docs` page is an interactive client FastAPI generates from our code.

## Recommended reading order

1. **This README, through “Run locally.”** Learn the request/response pieces above, then make one successful request in `/docs`. Change the weight to `-1` to see a validation error.
2. **[api/main.py](api/main.py).** Read the request model, response model, route, and pricing function in that order. These define what goes in, what comes out, and what happens between them. Leave the final Mangum adapter line until you get to AWS.
3. **[examples/call_api.py](examples/call_api.py).** See how another program builds a request and reads a response. It calls the server over HTTP rather than importing the pricing function. Run it against your local server before moving on.
4. **[scripts/build_lambda.py](scripts/build_lambda.py).** Learn how we collect our API code and its dependencies into a package Lambda can run. This prepares files locally; it does not create AWS resources.
5. **[cdk.json](cdk.json), then [infra/app.py](infra/app.py).** Follow the CDK entrypoint: `cdk.json` selects the Python command and output folder; `infra/app.py` creates the CDK app and adds our stack.
6. **[infra/stacks/shipping_quote_stack.py](infra/stacks/shipping_quote_stack.py).** Read the log group, Lambda function, API Gateway integration, and URL outputs. Then revisit the Mangum adapter in `api/main.py` and follow “Deploy with CDK” below.

You do not need to read `.venv/` or `.build/`: those contain installed libraries and generated files. The `requirements.txt` files are dependency lists; consult them when you want to know which packages belong to the API versus the deployment tools.

## Follow one request

Locally, Uvicorn is the web server listening on port 8000:

```text
Client → Uvicorn → FastAPI validates the JSON → shipping_quote() → JSON response
```

On AWS, API Gateway provides the HTTPS address and Lambda runs the code:

```text
Client → API Gateway → Lambda → Mangum → FastAPI → shipping_quote()
```

The response returns through the same services to the client. Mangum translates between API Gateway's event format and FastAPI's request/response interface. The pricing function is the same locally and on AWS.

For the 2 kg express example, validation succeeds, the function calculates `$10 + (2 × $2.50)`, and the client receives `$15` with a 2-day estimate. For a negative weight, validation returns `422` before the pricing function runs.

## Repository layout

```text
api/
  main.py                       # Endpoint, validation, and shipping calculation
  requirements.txt              # Packages included in Lambda
infra/
  app.py                        # CDK entrypoint
  stacks/
    shipping_quote_stack.py     # Lambda + API Gateway stack
  requirements.txt              # CDK dependencies
scripts/
  build_lambda.py               # Packages the API for Lambda
examples/
  call_api.py                   # Calls the API over HTTP
  call_aws_api.py               # Short caller for an AWS endpoint
cdk.json                        # CDK command and generated-output location
requirements.txt                # Local development/deployment dependencies
```

Installed libraries live in `.venv/`. Generated Lambda packages, CDK output, and deployment outputs live in `.build/`. Both folders are ignored by Git and separate from the source code.

## Set up

Use Python 3.11 or newer. For deployment, configure your AWS CLI and install the CDK CLI (`npm install -g aws-cdk`). Run all commands below from the repo root. Docker is not required.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Run locally

```bash
python -m uvicorn api.main:app --reload
```

`api.main:app` means “load the variable named `app` from `api/main.py`.” `--reload` restarts the local server when you edit the code. Leave this terminal running while you send requests.

Open http://127.0.0.1:8000/docs and try `POST /shipping-quote`:

```json
{"weight_kg": 2, "shipping_method": "express"}
```

Response:

```json
{"shipping_cost": 15.0, "currency": "USD", "estimated_days": 2}
```

These are fictional demo rates: standard is $5 + $2.50/kg with 5-day delivery; express is $10 + $2.50/kg with 2-day delivery. Weight must be greater than 0 and at most 100 kg. Try a negative weight or `"overnight"` to see FastAPI return a `422` validation error.

In another terminal, from the repo root:

```bash
source .venv/bin/activate
python examples/call_api.py
```

## Deploy with CDK

With the virtual environment activated:

```bash
aws sts get-caller-identity
python scripts/build_lambda.py
cdk bootstrap
cdk deploy --outputs-file .build/outputs.json
```

Bootstrap is only needed once per AWS account/region. The build script puts Linux-compatible API dependencies and `api/main.py` in `.build/lambda/`. CDK uploads that package and creates the Lambda, execution role, log group, and HTTP API.

CDK means **Cloud Development Kit**. It turns our Python infrastructure definitions into a **CloudFormation template**, a description AWS uses to create and update resources. A **stack** groups those resources into one deployment. These commands have different jobs:

| Command | What it does |
| --- | --- |
| `python scripts/build_lambda.py` | Collects the API and its runtime dependencies locally |
| `cdk synth` | Generates the CloudFormation template locally |
| `cdk bootstrap` | Prepares the account/region with shared CDK deployment resources |
| `cdk deploy` | Uploads the code and creates or updates the demo in AWS |
| `cdk destroy` | Deletes the demo stack from AWS |

CDK prints `ApiUrl` and `DocsUrl` after deployment. To update the API, run the build script and `cdk deploy` again. To preview the infrastructure locally, run `cdk synth` after building.

## Call the deployed demo

**Status: taken down on September 25, 2026.** The `ShippingQuoteDemo` stack in `us-east-1` has been deleted. The old URLs below are retained as examples and no longer work. Redeploy the stack and replace them with the new `ApiUrl` and `DocsUrl` outputs to run the demo again.

Previous docs URL (inactive): `https://jwf118tz9g.execute-api.us-east-1.amazonaws.com/docs`.

### Call it with curl

`curl` is a command-line tool for sending HTTP requests. Once the demo is deployed, anyone with curl and an internet connection can call its endpoint; no API key, Python installation, or copy of this repo is needed. Replace the retired URL below with your new deployment's URL.

Run this in a Bash or Zsh terminal, such as the default macOS terminal:

```bash
curl -X POST \
  https://jwf118tz9g.execute-api.us-east-1.amazonaws.com/shipping-quote \
  -H "Content-Type: application/json" \
  -d '{"weight_kg": 2, "shipping_method": "express"}'
```

Expected JSON response (shown formatted for readability):

```json
{
  "shipping_cost": 15.0,
  "currency": "USD",
  "estimated_days": 2
}
```

Here is what each part does:

| Part | Meaning |
| --- | --- |
| `curl` | Starts the HTTP client in your terminal. |
| `-X POST` | Sets the HTTP method to `POST`, matching our FastAPI route. |
| `https://` | Uses HTTPS to encrypt the connection. |
| `jwf118tz9g.execute-api.us-east-1.amazonaws.com` | The hostname AWS API Gateway assigned to this API. Together with `https://`, this is the base URL. |
| `/shipping-quote` | The route path that selects our shipping quote endpoint. |
| `-H "Content-Type: application/json"` | Adds a request header telling FastAPI that the body contains JSON. `-H` means “header.” |
| `-d '{"weight_kg": 2, "shipping_method": "express"}'` | Supplies the request body: the package weight and requested shipping method. `-d` means “data.” |
| Single quotes around the JSON | Tell the shell to pass the JSON as one argument, preserving its double quotes. The outer single quotes are not sent to the API. |
| `\` at the end of a line | Continues the same shell command onto the next line. It is for readability and is not part of the HTTP request. Do not put spaces after it. |

The method and URL tell the server **where to send the request and which operation to run**. The header describes the body's format, and the body provides the actual input values. FastAPI validates those values, runs the pricing function, and returns JSON for curl to print.

Using `-d` already makes curl default to `POST`; `-X POST` is included here to make the method explicit for the demo. Add `-i` after `curl` if you want to see the response status and headers as well as the JSON body. For example, a valid quote returns `200`; changing `weight_kg` to `-1` returns `422` with validation details.

### Call it with Python

The short AWS caller sends the same request as curl using Python's standard library. It does not deploy anything or require an API key. Pass the AWS **base URL** (without `/shipping-quote`); the script appends the route:

```bash
python examples/call_aws_api.py https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com
```

Replace the placeholder with an active endpoint's `ApiUrl`. Our previous demo endpoint has been deleted, so it cannot return a quote. The script is ready to use whenever an endpoint is available. Edit `payload` in [examples/call_aws_api.py](examples/call_aws_api.py) to change the weight or shipping method.

For the more heavily commented client with a local-server default, see [examples/call_api.py](examples/call_api.py).

Verified after the initial deployment: a 2 kg express quote returns $15 and 2 days; `/docs` returns `200`; a negative weight returns `422`.

## Delete after the demo

```bash
cdk destroy
```

This removes the demo API, Lambda, role, and log group. The shared CDK bootstrap stack and deployment assets remain. The endpoint is public, and AWS usage can incur charges.
