import * as path from "node:path";

import {
  CfnOutput,
  Duration,
  RemovalPolicy,
  Stack,
  type StackProps,
} from "aws-cdk-lib";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as lambdaEventSources from "aws-cdk-lib/aws-lambda-event-sources";
import * as lambdaNodejs from "aws-cdk-lib/aws-lambda-nodejs";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as s3Notifications from "aws-cdk-lib/aws-s3-notifications";
import * as secretsmanager from "aws-cdk-lib/aws-secretsmanager";
import * as sqs from "aws-cdk-lib/aws-sqs";
import type { Construct } from "constructs";

export const OPENAI_SECRET_NAME = "contract-clause-demo/openai-api-key";
export const DATABASE_SECRET_NAME = "contract-clause-demo/neon-database-url";

export interface ContractPipelineStackProps extends StackProps {
  openAiModel: string;
}

export class ContractPipelineStack extends Stack {
  public constructor(
    scope: Construct,
    id: string,
    props: ContractPipelineStackProps,
  ) {
    super(scope, id, props);

    const contractsBucket = new s3.Bucket(this, "ContractsBucket", {
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      enforceSSL: true,
      autoDeleteObjects: true,
      removalPolicy: RemovalPolicy.DESTROY,
    });

    const deadLetterQueue = new sqs.Queue(this, "ProcessingDeadLetterQueue", {
      retentionPeriod: Duration.days(14),
    });

    const processingQueue = new sqs.Queue(this, "ProcessingQueue", {
      visibilityTimeout: Duration.minutes(12),
      retentionPeriod: Duration.days(4),
      deadLetterQueue: {
        queue: deadLetterQueue,
        maxReceiveCount: 3,
      },
    });

    const openAiSecret = new secretsmanager.Secret(this, "OpenAiApiKey", {
      secretName: OPENAI_SECRET_NAME,
      description: "OpenAI API key used by the contract clause demo.",
      generateSecretString: {
        excludePunctuation: true,
        passwordLength: 32,
      },
    });

    const databaseSecret = new secretsmanager.Secret(this, "NeonDatabaseUrl", {
      secretName: DATABASE_SECRET_NAME,
      description: "Pooled Neon DATABASE_URL used by the contract clause demo.",
      generateSecretString: {
        excludePunctuation: true,
        passwordLength: 32,
      },
    });

    const dispatcher = new lambdaNodejs.NodejsFunction(this, "Dispatcher", {
      entry: path.join(__dirname, "../lambdas/dispatcher/index.ts"),
      runtime: lambda.Runtime.NODEJS_22_X,
      handler: "handler",
      timeout: Duration.minutes(2),
      memorySize: 256,
      environment: {
        PROCESSING_QUEUE_URL: processingQueue.queueUrl,
      },
      bundling: {
        minify: true,
        sourceMap: true,
      },
    });

    const processor = new lambdaNodejs.NodejsFunction(this, "Processor", {
      entry: path.join(__dirname, "../lambdas/processor/index.ts"),
      runtime: lambda.Runtime.NODEJS_22_X,
      handler: "handler",
      timeout: Duration.minutes(10),
      memorySize: 1024,
      reservedConcurrentExecutions: 5,
      environment: {
        OPENAI_SECRET_NAME,
        DATABASE_SECRET_NAME,
        OPENAI_MODEL: props.openAiModel,
        MAX_PDF_BYTES: String(10 * 1024 * 1024),
        MAX_CONTRACT_CHARACTERS: "250000",
      },
      bundling: {
        minify: true,
        sourceMap: true,
        nodeModules: ["pdf-parse"],
      },
    });

    contractsBucket.grantRead(dispatcher);
    contractsBucket.grantRead(processor);
    processingQueue.grantSendMessages(dispatcher);
    openAiSecret.grantRead(processor);
    databaseSecret.grantRead(processor);

    contractsBucket.addEventNotification(
      s3.EventType.OBJECT_CREATED,
      new s3Notifications.LambdaDestination(dispatcher),
      { prefix: "manifests/", suffix: ".csv" },
    );

    processor.addEventSource(
      new lambdaEventSources.SqsEventSource(processingQueue, {
        batchSize: 1,
        maxConcurrency: 5,
        reportBatchItemFailures: true,
      }),
    );

    new CfnOutput(this, "ContractsBucketName", {
      value: contractsBucket.bucketName,
    });
    new CfnOutput(this, "ProcessingQueueUrl", {
      value: processingQueue.queueUrl,
    });
    new CfnOutput(this, "DeadLetterQueueUrl", {
      value: deadLetterQueue.queueUrl,
    });
  }
}
