import { sql } from "drizzle-orm";
import {
  check,
  integer,
  pgTable,
  serial,
  text,
  timestamp,
  uniqueIndex,
} from "drizzle-orm/pg-core";

export const contractClauses = pgTable(
  "contract_clauses",
  {
    id: serial("id").primaryKey(),
    customerId: text("customer_id").notNull(),
    contractId: text("contract_id").notNull(),
    companyName: text("company_name").notNull(),
    clauseType: text("clause_type").notNull(),
    correspondingClauseText: text("corresponding_clause_text"),
    occurrenceIndex: integer("occurrence_index").notNull().default(0),
    sourceS3Key: text("source_s3_key").notNull(),
    model: text("model").notNull(),
    processedAt: timestamp("processed_at", { withTimezone: true })
      .notNull()
      .defaultNow(),
  },
  (table) => [
    uniqueIndex("contract_clause_occurrence_unique").on(
      table.customerId,
      table.contractId,
      table.clauseType,
      table.occurrenceIndex,
    ),
    check(
      "contract_clause_type_check",
      sql`${table.clauseType} in ('TechUpgrade', 'Confidentiality', 'Renewal', 'NA')`,
    ),
  ],
);
