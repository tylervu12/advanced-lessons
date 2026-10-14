# Contract Clause Extraction

An AWS pipeline that reads contract manifests from S3, queues processing through
SQS, extracts clauses with OpenAI, and stores the results in Neon Postgres.
