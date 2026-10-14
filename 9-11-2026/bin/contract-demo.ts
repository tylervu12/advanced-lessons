#!/usr/bin/env node

import "dotenv/config";
import "source-map-support/register";

import { App } from "aws-cdk-lib";

import { ContractPipelineStack } from "../lib/contract-pipeline-stack";

const app = new App();

new ContractPipelineStack(app, "ContractClauseDemoStack", {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.AWS_REGION ?? "us-east-2",
  },
  openAiModel: process.env.OPENAI_MODEL ?? "gpt-5-mini",
});
