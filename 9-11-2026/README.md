# Contract clause extraction demo

This project deploys a small AWS pipeline that reads a CSV manifest from S3,
queues each contract through SQS, extracts selectable text from each PDF, asks
the OpenAI Responses API to identify target clauses, and writes the results to
Neon Postgres.

```text
S3 manifest -> dispatcher Lambda -> SQS -> processor Lambda -> OpenAI -> Neon
                                      |
                                      +-> dead-letter queue after 3 failures
```

The demo recognizes these clause types:

- `TechUpgrade`
- `Confidentiality`
- `Renewal`
- `NA` when the contract contains none of the target clauses

## Demo limits

- PDFs must contain selectable text. Scanned PDFs fail into the DLQ because this
  demo does not include OCR or Textract.
- A PDF may be at most 10 MB and its extracted text may be at most 250,000
  characters.
- Processor concurrency is capped at five to avoid unexpectedly high API use.
- One contract may produce multiple rows when multiple matching clauses exist.

## Prerequisites

- Node.js 22 or newer
- AWS CLI credentials for the target AWS account
- AWS CDK bootstrapped in `us-east-2`
- The linked Neon project and branch
- A valid OpenAI API key

The repository contains the Neon config template. Link your own Neon project
locally; the local `.neon` service link is excluded from Git. Install project
dependencies with:

```bash
npm install
```

## Environment

Keep `.env` local. It is ignored by Git and should contain:

```dotenv
OPENAI_API_KEY=your-rotated-key
OPENAI_MODEL=gpt-5-mini
DATABASE_URL=your-pooled-neon-url
DATABASE_URL_UNPOOLED=your-direct-neon-url
NEON_BRANCH=production
AWS_REGION=us-east-2
```

Use the pooled `DATABASE_URL` in Lambda and the direct
`DATABASE_URL_UNPOOLED` for schema migrations.

## Verify the project

```bash
npm run check
```

This runs the TypeScript compiler, unit tests, Lambda bundling tests, and
`cdk synth`.

## Create the database schema

Review the SQL in `drizzle/`, then apply it to the currently configured Neon
database:

```bash
npm run db:migrate
```

The internal table is `contract_clauses`. The view
`contract_clause_export` exposes the requested five columns:

```text
CustomerID
ContractID
CompanyName
ClauseType
CorrespondingClauseText
```

## Deploy AWS resources

Bootstrap once if the AWS account and region have not used CDK before:

```bash
cdk bootstrap
```

Deploy the stack:

```bash
npm run deploy
```

The deployment outputs the S3 bucket name, processing queue URL, and DLQ URL.
After the stack exists, copy the local OpenAI and Neon values into the two AWS
Secrets Manager secrets:

```bash
npm run secrets:sync
```

Secret values are never placed in the CDK template or committed files.

## Run the demo

Get the generated bucket name:

```bash
BUCKET_NAME=$(aws cloudformation describe-stacks \
  --stack-name ContractClauseDemoStack \
  --region us-east-2 \
  --query 'Stacks[0].Outputs[?OutputKey==`ContractsBucketName`].OutputValue' \
  --output text)
```

Upload a selectable-text PDF using the same key referenced by the manifest:

```bash
aws s3 cp ./example-contract.pdf "s3://${BUCKET_NAME}/contracts/example-contract.pdf"
```

Then upload the manifest. Uploading under `manifests/` triggers the pipeline:

```bash
aws s3 cp ./examples/manifest.csv "s3://${BUCKET_NAME}/manifests/demo.csv"
```

Query the result:

```bash
neon psql production -- -c 'SELECT * FROM contract_clause_export ORDER BY "CustomerID", "ContractID", "ClauseType";'
```

If processing fails three times, inspect the `DeadLetterQueueUrl` stack output
and the processor Lambda logs in CloudWatch.

## Manifest format

The header names are required exactly as shown:

```csv
CustomerID,ContractID,CompanyName,S3Key
customer-001,contract-001,Example Health,contracts/example-contract.pdf
```

`S3Key` is the object key inside the deployed contract bucket, without an
`s3://` prefix.

## Remove the demo

The bucket and queues use demo-friendly removal policies. Empty resources and
remove the AWS stack with:

```bash
npm run destroy
```

Destroying the AWS stack does not delete the Neon table or view.
