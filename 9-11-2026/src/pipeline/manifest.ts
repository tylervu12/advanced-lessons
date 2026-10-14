import { z } from "zod";

export const manifestRowSchema = z.object({
  CustomerID: z.string().trim().min(1),
  ContractID: z.string().trim().min(1),
  CompanyName: z.string().trim().min(1),
  S3Key: z.string().trim().min(1),
});

export type ManifestRow = z.infer<typeof manifestRowSchema>;

export interface ProcessingMessage {
  customerId: string;
  contractId: string;
  companyName: string;
  bucket: string;
  s3Key: string;
}

export function toProcessingMessage(
  row: ManifestRow,
  bucket: string,
): ProcessingMessage {
  const parsed = manifestRowSchema.parse(row);

  return {
    customerId: parsed.CustomerID,
    contractId: parsed.ContractID,
    companyName: parsed.CompanyName,
    bucket,
    s3Key: parsed.S3Key,
  };
}

export const processingMessageSchema = z.object({
  customerId: z.string().min(1),
  contractId: z.string().min(1),
  companyName: z.string().min(1),
  bucket: z.string().min(1),
  s3Key: z.string().min(1),
});
