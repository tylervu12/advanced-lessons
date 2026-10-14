import { App } from "aws-cdk-lib";
import { Match, Template } from "aws-cdk-lib/assertions";
import { describe, expect, it } from "vitest";

import { ContractPipelineStack } from "../lib/contract-pipeline-stack";

describe("ContractPipelineStack", () => {
  const app = new App();
  const stack = new ContractPipelineStack(app, "TestStack", {
    openAiModel: "gpt-5-mini",
  });
  const template = Template.fromStack(stack);

  it("creates the processing queue and its dead-letter queue", () => {
    template.resourceCountIs("AWS::SQS::Queue", 2);
    template.hasResourceProperties("AWS::SQS::Queue", {
      RedrivePolicy: Match.objectLike({ maxReceiveCount: 3 }),
    });
  });

  it("limits processor concurrency and consumes one contract at a time", () => {
    template.hasResourceProperties("AWS::Lambda::Function", {
      ReservedConcurrentExecutions: 5,
      Environment: {
        Variables: Match.objectLike({ OPENAI_MODEL: "gpt-5-mini" }),
      },
    });
    template.hasResourceProperties("AWS::Lambda::EventSourceMapping", {
      BatchSize: 1,
      FunctionResponseTypes: ["ReportBatchItemFailures"],
    });
    expect(template.toJSON()).toBeTruthy();
  });
});
