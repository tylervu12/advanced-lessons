# Advanced Lessons

Five standalone lessons covering AWS pipelines, FastAPI, testing, and machine learning.

| Date | Lesson | Start here |
| --- | --- | --- |
| September 11, 2026 | Contract clause extraction with AWS, OpenAI, and Neon | [README](9-11-2026/README.md) |
| September 18, 2026 | Business website classification with FastAPI and OpenAI | [README](9-18-2026/README.md) |
| September 25, 2026 | Shipping quote API and AWS CDK deployment | [README](9-25-2026/README.md) |
| October 2, 2026 | Store API with unit, integration, and end-to-end tests | [README](10-2-2026/README.md) |
| October 9, 2026 | Predicting California house prices | [Notebook](10-9-2026/house_prices_demo.ipynb) |

## Running a lesson

Change into the lesson's dated directory before following its instructions. Each
lesson manages its own dependencies; recreate Python virtual environments or run
`npm install` as appropriate. The machine learning lesson includes its dataset
and `requirements.txt`.

For lessons that require credentials, copy `.env.example` to `.env` inside that
lesson and fill in your own values. Configure your own AWS and Neon resources.
Local credentials, service links, dependency folders, generated deployment
artifacts, and earlier Git histories are excluded from this repository.

The workflow in `10-2-2026/.github/workflows/` is a standalone lesson example;
GitHub does not run workflows nested below the repository root.

## Secret audit

Before the initial publication, Gitleaks 8.30.1 scanned the publication files.
Additional checks compared files against local environment values and inspected
notebook outputs and extracted sample PDF text. No secrets were detected. Scans
reduce risk but cannot guarantee that every possible secret is detected.
