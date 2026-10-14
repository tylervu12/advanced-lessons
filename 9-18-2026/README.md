# Business Website Classifier

A FastAPI service that maps a business website to one predefined category. The
application sends the URL and taxonomy to the OpenAI Responses API. OpenAI's
hosted web-search tool inspects the website and can search for corroborating
information when the site is sparse or unavailable.

The application does not download, scrape, or inject website HTML into the prompt.

## How it works

1. `POST /classify` accepts a public HTTP or HTTPS URL.
2. FastAPI validates the URL but does not connect to it.
3. The OpenAI Responses API receives the URL, category definitions, and the
   `web_search` tool.
4. The model starts with the supplied website. When needed, it searches for the
   exact domain and associated company using public sources.
5. Structured Outputs restricts the result to the predefined taxonomy and response schema.
6. The API returns the category, confidence, reason, research method, and sources.

Website content is treated as untrusted evidence. The classifier is explicitly
instructed to ignore instructions found in pages or search results.

## Setup

Create a virtual environment and install the dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Add your OpenAI API key to `.env`:

```env
OPENAI_API_KEY=your_real_key_here
OPENAI_MODEL=gpt-5.5
OPENAI_SEARCH_CONTEXT_SIZE=medium
```

`.env` is ignored by Git. Keep `.env.example` as the shareable configuration template.

Start the API:

```bash
uvicorn app.main:app --reload
```

Open the interactive API documentation at <http://127.0.0.1:8000/docs>.

## Classify a website

```bash
curl -X POST http://127.0.0.1:8000/classify \
  -H "Content-Type: application/json" \
  -d '{"url":"https://code.visualstudio.com/"}'
```

Example response:

```json
{
  "url": "https://code.visualstudio.com/",
  "business_name": "Visual Studio Code",
  "category": "Software",
  "confidence": 0.98,
  "reason": "The website presents a software code editor.",
  "research_method": "website_only",
  "sources": [
    {
      "title": "Visual Studio Code",
      "url": "https://code.visualstudio.com/"
    }
  ]
}
```

`research_method` explains how the result was obtained:

- `website_only`: the supplied website was sufficient.
- `website_plus_search`: the website and outside search evidence were used.
- `search_only`: the website could not be used, but outside sources were sufficient.
- `insufficient`: reliable classification was not possible.

The confidence value is the model's evidence-based assessment. It is useful for
routing low-confidence results to human review, but it is not a calibrated probability.

## Other endpoints

`GET /health` returns service status and whether an API key is configured. It
never returns the key itself.

## Tests

The automated tests mock the OpenAI client and do not use API credits:

```bash
pytest
```

## Current limitation

OpenAI web search may be unable to access sites that block indexing or require a
login. The classifier then uses corroborating sources when it can confirm that
they refer to the same organization. Otherwise, it returns
`Unknown / Insufficient Information`.
