import { GetObjectCommand, S3Client } from "@aws-sdk/client-s3";
import { SendMessageBatchCommand, SQSClient } from "@aws-sdk/client-sqs";
import type { S3Event } from "aws-lambda";
import { parse } from "csv-parse/sync";

import {
  manifestRowSchema,
  toProcessingMessage,
  type ManifestRow,
} from "../../src/pipeline/manifest";

const s3 = new S3Client({});
const sqs = new SQSClient({});

const queueUrl = process.env.PROCESSING_QUEUE_URL;
if (!queueUrl) {
  throw new Error("PROCESSING_QUEUE_URL is not configured");
}

export async function handler(event: S3Event): Promise<void> {
  for (const record of event.Records) {
    const bucket = record.s3.bucket.name;
    const manifestKey = decodeURIComponent(
      record.s3.object.key.replace(/\+/g, " "),
    );

    const object = await s3.send(
      new GetObjectCommand({ Bucket: bucket, Key: manifestKey }),
    );
    if (!object.Body) {
      throw new Error(`Manifest ${manifestKey} has no body`);
    }

    const csv = await object.Body.transformToString();
    const rawRows = parse(csv, {
      columns: true,
      bom: true,
      skip_empty_lines: true,
      trim: true,
    }) as unknown[];

    const rows = rawRows.map((row, index) => {
      const parsed = manifestRowSchema.safeParse(row);
      if (!parsed.success) {
        throw new Error(
          `Invalid manifest row ${index + 2}: ${parsed.error.message}`,
        );
      }
      return parsed.data;
    });

    await sendRows(bucket, rows);
    console.log(
      JSON.stringify({ event: "manifest_dispatched", manifestKey, rows: rows.length }),
    );
  }
}

async function sendRows(bucket: string, rows: ManifestRow[]): Promise<void> {
  for (let offset = 0; offset < rows.length; offset += 10) {
    const batch = rows.slice(offset, offset + 10);
    const response = await sqs.send(
      new SendMessageBatchCommand({
        QueueUrl: queueUrl,
        Entries: batch.map((row, index) => ({
          Id: String(offset + index),
          MessageBody: JSON.stringify(toProcessingMessage(row, bucket)),
        })),
      }),
    );

    if (response.Failed && response.Failed.length > 0) {
      throw new Error(
        `SQS rejected ${response.Failed.length} manifest rows: ${response.Failed.map((failure) => failure.Message ?? failure.Code).join(", ")}`,
      );
    }
  }
}
