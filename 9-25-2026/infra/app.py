"""Read fourth, alongside cdk.json: this is the entrypoint for CDK commands.

The repo's cdk.json tells the CDK CLI to run: python infra/app.py
This describes infrastructure; it is not the FastAPI web application.
"""

# A CDK App is a container for one or more infrastructure stacks.
from aws_cdk import App

# Our stack definition lives in its own file so it is easy to find and read.
from stacks.shipping_quote_stack import ShippingQuoteStack

app = App()

# A stack groups AWS resources into one CloudFormation deployment.
# Keep this name stable when updating or deleting the existing demo.
ShippingQuoteStack(app, "ShippingQuoteDemo")

# Synthesis turns the Python definitions into a CloudFormation template.
# cdk.json puts that generated output under .build/cdk.out/.
# "cdk synth" only generates the template; "cdk deploy" uses it to create/update
# resources in AWS. Running this Python file alone does not deploy the API.
app.synth()
