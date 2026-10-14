"""Read fifth: define the AWS resources that run our shipping API.

API Gateway provides the public HTTPS URL. Lambda runs the Python code.
CloudWatch Logs stores Lambda's logs so you can inspect failures.
"""

from pathlib import Path

# CDK is infrastructure as code: Python objects describe AWS resources.
# CfnOutput prints useful values after deployment, such as the public URL.
from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_apigatewayv2 as apigateway
from aws_cdk import aws_apigatewayv2_integrations as integrations
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
# A construct is a building block in CDK's resource tree. A Stack is one kind.
from constructs import Construct

# This file is under infra/stacks/, so go up two directories to the repo root.
ROOT = Path(__file__).resolve().parents[2]


class ShippingQuoteStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        # scope is the parent CDK App; construct_id is "ShippingQuoteDemo".
        # Initialize the parent Stack before adding resources inside it.
        super().__init__(scope, construct_id, **kwargs)

        # 1. LOGS: give Lambda a CloudWatch log group.
        # "self" makes it part of this stack. "ApiLogs" is its CDK identifier.
        # Keep these identifiers stable to preserve resource identity on updates.
        log_group = logs.LogGroup(
            self, "ApiLogs",
            # Expire log events after one day for this temporary demo.
            retention=logs.RetentionDays.ONE_DAY,
            # Also delete the log group when we run cdk destroy.
            removal_policy=RemovalPolicy.DESTROY,
        )

        # 2. COMPUTE: Lambda runs our API code when a request arrives.
        # CDK also creates its execution role, which permits writing Lambda logs.
        function = lambda_.Function(
            self, "ShippingApi",
            # Match the Python version and CPU architecture in build_lambda.py.
            runtime=lambda_.Runtime.PYTHON_3_11,
            architecture=lambda_.Architecture.X86_64,

            # "main.handler" means the handler variable inside packaged main.py.
            # That variable is the Mangum adapter around our FastAPI app.
            handler="main.handler",

            # CDK packages this folder as an asset and uploads it during deployment.
            # Run scripts/build_lambda.py first so the folder exists and is current.
            code=lambda_.Code.from_asset(str(ROOT / ".build" / "lambda")),

            # Allocate 256 MB of memory and stop an invocation after 10 seconds.
            memory_size=256,
            timeout=Duration.seconds(10),
            log_group=log_group,
        )

        # 3. PUBLIC URL: API Gateway receives HTTP requests from clients.
        # The default integration forwards all paths to Lambda, so FastAPI handles
        # /shipping-quote, /docs, /openapi.json, and 404s for unknown routes.
        # CDK also grants API Gateway permission to invoke this Lambda.
        api = apigateway.HttpApi(
            self, "HttpApi",
            default_integration=integrations.HttpLambdaIntegration("LambdaIntegration", function),
        )

        # These outputs appear in the terminal after cdk deploy.
        # --outputs-file .build/outputs.json also saves them for later use.
        # ApiUrl goes into examples/call_api.py; DocsUrl opens the browser tester.
        CfnOutput(self, "ApiUrl", value=api.api_endpoint)
        CfnOutput(self, "DocsUrl", value=f"{api.api_endpoint}/docs")
