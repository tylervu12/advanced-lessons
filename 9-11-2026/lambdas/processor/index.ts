import { GetObjectCommand, S3Client } from "@aws-sdk/client-s3";
import {
  GetSecretValueCommand,
  SecretsManagerClient,
} from "@aws-sdk/client-secrets-manager";
import { neon } from "@neondatabase/serverless";
import type { SQSEvent, SQSBatchResponse } from "aws-lambda";
import OpenAI from "openai";
import { zodTextFormat } from "openai/helpers/zod";
import pdfParse from "pdf-parse";

import {
  modelOutputSchema,
  normalizeClauses,
} from "../../src/pipeline/clauses";
import { processingMessageSchema } from "../../src/pipeline/manifest";

const s3 = new S3Client({});
const secrets = new SecretsManagerClient({});
const secretCache = new Map<string, Promise<string>>();

const openAiSecretName = requiredEnv("OPENAI_SECRET_NAME");
const databaseSecretName = requiredEnv("DATABASE_SECRET_NAME");
const openAiModel = process.env.OPENAI_MODEL ?? "gpt-5-mini";
const maxPdfBytes = Number(process.env.MAX_PDF_BYTES ?? 10 * 1024 * 1024);
const maxContractCharacters = Number(
  process.env.MAX_CONTRACT_CHARACTERS ?? 250_000,
);

export async function handler(event: SQSEvent): Promise<SQSBatchResponse> {
  const batchItemFailures: SQSBatchResponse["batchItemFailures"] = [];

  for (const record of event.Records) {
    try {
      const message = processingMessageSchema.parse(JSON.parse(record.body));
      await processContract(message);
    } catch (error) {
      console.error(
        JSON.stringify({
          event: "contract_processing_failed",
          messageId: record.messageId,
          error: error instanceof Error ? error.message : String(error),
        }),
      );
      batchItemFailures.push({ itemIdentifier: record.messageId });
    }
  }

  return { batchItemFailures };
}

async function processContract(message: {
  customerId: string;
  contractId: string;
  companyName: string;
  bucket: string;
  s3Key: string;
}): Promise<void> {
  if (!message.s3Key.toLowerCase().endsWith(".pdf")) {
    throw new Error(`Only PDF contracts are supported: ${message.s3Key}`);
  }

  const object = await s3.send(
    new GetObjectCommand({ Bucket: message.bucket, Key: message.s3Key }),
  );
  if (!object.Body) {
    throw new Error(`Contract ${message.s3Key} has no body`);
  }

  const bytes = await object.Body.transformToByteArray();
  if (bytes.byteLength > maxPdfBytes) {
    throw new Error(
      `PDF is ${bytes.byteLength} bytes; demo limit is ${maxPdfBytes} bytes`,
    );
  }

  const parsedPdf = await pdfParse(Buffer.from(bytes));
  const contractText = parsedPdf.text.trim();
  if (!contractText) {
    throw new Error(
      "The PDF has no selectable text. This demo does not include OCR/Textract.",
    );
  }
  if (contractText.length > maxContractCharacters) {
    throw new Error(
      `Contract has ${contractText.length} characters; demo limit is ${maxContractCharacters}`,
    );
  }

  const openAiKey = await getSecret(openAiSecretName);
  const client = new OpenAI({ apiKey: openAiKey });
  const response = await client.responses.parse({
    model: openAiModel,
    store: false,
    input: [
      {
        role: "system",
        content:
          "Extract contract clauses. Return TechUpgrade for terms requiring or governing technology upgrades, Confidentiality for confidentiality or nondisclosure duties, and Renewal for renewal, extension, or auto-renewal terms. Copy the complete relevant clause text exactly from the contract. Do not summarize or invent text. Return an empty clauses array when none apply.",
      },
      {
        role: "user",
        content: `Customer: ${message.companyName}\nContract ID: ${message.contractId}\n\nCONTRACT TEXT:\n${contractText}`,
      },
    ],
    text: {
      format: zodTextFormat(modelOutputSchema, "contract_clauses"),
    },
  });

  if (!response.output_parsed) {
    throw new Error("OpenAI returned no parsed clause result");
  }

  const normalized = normalizeClauses(response.output_parsed.clauses);
  const databaseUrl = await getSecret(databaseSecretName);
  const sql = neon(databaseUrl);
  const queries = [
    sql`DELETE FROM contract_clauses
        WHERE customer_id = ${message.customerId}
          AND contract_id = ${message.contractId}`,
    ...normalized.map(
      (clause) => sql`INSERT INTO contract_clauses (
          customer_id,
          contract_id,
          company_name,
          clause_type,
          corresponding_clause_text,
          occurrence_index,
          source_s3_key,
          model
        ) VALUES (
          ${message.customerId},
          ${message.contractId},
          ${message.companyName},
          ${clause.clauseType},
          ${clause.correspondingClauseText},
          ${clause.occurrenceIndex},
          ${message.s3Key},
          ${openAiModel}
        )`,
    ),
  ];

  await sql.transaction(queries);
  console.log(
    JSON.stringify({
      event: "contract_processed",
      customerId: message.customerId,
      contractId: message.contractId,
      clauses: normalized.length,
    }),
  );
}

function requiredEnv(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`${name} is not configured`);
  }
  return value;
}

function getSecret(name: string): Promise<string> {
  const existing = secretCache.get(name);
  if (existing) {
    return existing;
  }

  const pending = secrets
    .send(new GetSecretValueCommand({ SecretId: name }))
    .then((response) => {
      if (!response.SecretString) {
        throw new Error(`Secret ${name} does not contain a string value`);
      }
      return response.SecretString;
    });
  secretCache.set(name, pending);
  return pending;
}
