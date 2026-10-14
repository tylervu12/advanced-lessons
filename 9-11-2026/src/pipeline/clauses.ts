import { z } from "zod";

export const supportedClauseTypes = [
  "TechUpgrade",
  "Confidentiality",
  "Renewal",
] as const;

export const modelClauseSchema = z.object({
  clauseType: z.enum(supportedClauseTypes),
  correspondingClauseText: z.string(),
});

export const modelOutputSchema = z.object({
  clauses: z.array(modelClauseSchema),
});

export type ModelClause = z.infer<typeof modelClauseSchema>;

export interface StoredClause {
  clauseType: ModelClause["clauseType"] | "NA";
  correspondingClauseText: string | null;
  occurrenceIndex: number;
}

export function normalizeClauses(clauses: ModelClause[]): StoredClause[] {
  const seen = new Set<string>();
  const occurrenceByType = new Map<string, number>();
  const normalized: StoredClause[] = [];

  for (const clause of clauses) {
    const text = clause.correspondingClauseText.trim();
    if (!text) {
      continue;
    }
    const dedupeKey = `${clause.clauseType}:${text}`;
    if (seen.has(dedupeKey)) {
      continue;
    }

    seen.add(dedupeKey);
    const occurrenceIndex = occurrenceByType.get(clause.clauseType) ?? 0;
    occurrenceByType.set(clause.clauseType, occurrenceIndex + 1);
    normalized.push({
      clauseType: clause.clauseType,
      correspondingClauseText: text,
      occurrenceIndex,
    });
  }

  return normalized.length > 0
    ? normalized
    : [
        {
          clauseType: "NA",
          correspondingClauseText: null,
          occurrenceIndex: 0,
        },
      ];
}
