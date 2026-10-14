import "dotenv/config";

import {
  PutSecretValueCommand,
  SecretsManagerClient,
} from "@aws-sdk/client-secrets-manager";

import {
  DATABASE_SECRET_NAME,
  OPENAI_SECRET_NAME,
} from "../lib/contract-pipeline-stack";

async function main(): Promise<void> {
  const openAiKey = requiredEnv("OPENAI_API_KEY");
  const databaseUrl = requiredEnv("DATABASE_URL");
  const region = process.env.AWS_REGION ?? "us-east-2";
  const client = new SecretsManagerClient({ region });

  await Promise.all([
    putSecret(client, OPENAI_SECRET_NAME, openAiKey),
    putSecret(client, DATABASE_SECRET_NAME, databaseUrl),
  ]);

  console.log(
    `Synced ${OPENAI_SECRET_NAME} and ${DATABASE_SECRET_NAME} in ${region}.`,
  );
}

async function putSecret(
  client: SecretsManagerClient,
  secretId: string,
  value: string,
): Promise<void> {
  await client.send(
    new PutSecretValueCommand({ SecretId: secretId, SecretString: value }),
  );
}

void main().catch((error: unknown) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exitCode = 1;
});

function requiredEnv(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`${name} is missing from .env`);
  }
  return value;
}
