CREATE TABLE "contract_clauses" (
	"id" serial PRIMARY KEY NOT NULL,
	"customer_id" text NOT NULL,
	"contract_id" text NOT NULL,
	"company_name" text NOT NULL,
	"clause_type" text NOT NULL,
	"corresponding_clause_text" text,
	"occurrence_index" integer DEFAULT 0 NOT NULL,
	"source_s3_key" text NOT NULL,
	"model" text NOT NULL,
	"processed_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "contract_clause_type_check" CHECK ("contract_clauses"."clause_type" in ('TechUpgrade', 'Confidentiality', 'Renewal', 'NA'))
);
--> statement-breakpoint
CREATE UNIQUE INDEX "contract_clause_occurrence_unique" ON "contract_clauses" USING btree ("customer_id","contract_id","clause_type","occurrence_index");
--> statement-breakpoint
CREATE VIEW "contract_clause_export" AS
SELECT
	"customer_id" AS "CustomerID",
	"contract_id" AS "ContractID",
	"company_name" AS "CompanyName",
	"clause_type" AS "ClauseType",
	"corresponding_clause_text" AS "CorrespondingClauseText"
FROM "contract_clauses";
