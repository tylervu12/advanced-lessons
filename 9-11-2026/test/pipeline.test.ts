import { describe, expect, it } from "vitest";

import { normalizeClauses } from "../src/pipeline/clauses";
import { toProcessingMessage } from "../src/pipeline/manifest";

describe("manifest mapping", () => {
  it("maps the documented CSV columns to a queue message", () => {
    expect(
      toProcessingMessage(
        {
          CustomerID: " customer-1 ",
          ContractID: "contract-9",
          CompanyName: "Acme Health",
          S3Key: "contracts/acme.pdf",
        },
        "demo-bucket",
      ),
    ).toEqual({
      customerId: "customer-1",
      contractId: "contract-9",
      companyName: "Acme Health",
      bucket: "demo-bucket",
      s3Key: "contracts/acme.pdf",
    });
  });
});

describe("clause normalization", () => {
  it("deduplicates exact clauses and assigns occurrence indexes by type", () => {
    expect(
      normalizeClauses([
        {
          clauseType: "Renewal",
          correspondingClauseText: " Renews every year. ",
        },
        {
          clauseType: "Renewal",
          correspondingClauseText: "Renews every year.",
        },
        {
          clauseType: "Renewal",
          correspondingClauseText: "Either party may opt out.",
        },
      ]),
    ).toEqual([
      {
        clauseType: "Renewal",
        correspondingClauseText: "Renews every year.",
        occurrenceIndex: 0,
      },
      {
        clauseType: "Renewal",
        correspondingClauseText: "Either party may opt out.",
        occurrenceIndex: 1,
      },
    ]);
  });

  it("creates an NA row when no target clause exists", () => {
    expect(normalizeClauses([])).toEqual([
      {
        clauseType: "NA",
        correspondingClauseText: null,
        occurrenceIndex: 0,
      },
    ]);
  });

  it("ignores empty clause text returned by the model", () => {
    expect(
      normalizeClauses([
        { clauseType: "Confidentiality", correspondingClauseText: "   " },
      ]),
    ).toEqual([
      {
        clauseType: "NA",
        correspondingClauseText: null,
        occurrenceIndex: 0,
      },
    ]);
  });
});
