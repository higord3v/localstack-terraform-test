import json
import logging
import os
import time
import uuid

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# The state machine ARN is injected by Terraform through the SM_ARN environment
# variable. Derive the region from the ARN itself so the client always targets
# the same region the state machine was created in, instead of hardcoding one.
_STATE_MACHINE_ARN = os.environ.get("SM_ARN", "")
_ARN_PARTS = _STATE_MACHINE_ARN.split(":")
_REGION = (
    _ARN_PARTS[3]
    if len(_ARN_PARTS) > 4 and _ARN_PARTS[3]
    else os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
)

# Under LocalStack the Lambda runs in a sibling container, so it must reach the
# LocalStack edge port through the container hostname rather than localhost.
# AWS_ENDPOINT_URL is set by LocalStack; LOCALSTACK_HOSTNAME is the fallback.
_ENDPOINT_URL = os.environ.get("AWS_ENDPOINT_URL")
if not _ENDPOINT_URL:
    _localstack_host = os.environ.get("LOCALSTACK_HOSTNAME")
    if _localstack_host:
        _ENDPOINT_URL = (
            f"http://{_localstack_host}:{os.environ.get('EDGE_PORT', '4566')}"
        )

sfn_client = boto3.client(
    "stepfunctions", region_name=_REGION, endpoint_url=_ENDPOINT_URL
)


def generate_execution_name():
    unique_id = str(uuid.uuid4())
    current_time = int(time.time())
    execution_name = f"Execution-{current_time}-{unique_id}"
    return execution_name


def lambda_handler(event, context):
    s3_bucket = event["Records"][0]["s3"]["bucket"]["name"]
    s3_object_key = event["Records"][0]["s3"]["object"]["key"]

    input_data = {"bucket": s3_bucket, "fileName": s3_object_key}

    logger.info(f"Input Data: {input_data}")
    logger.info(f"Event: {event}")

    # Define the Step Function's ARN
    state_machine_arn = os.environ.get("SM_ARN")

    # Start the Step Function execution
    response = sfn_client.start_execution(
        stateMachineArn=state_machine_arn,
        name=generate_execution_name(),
        input=json.dumps(input_data),
    )

    # Log the response for debugging
    logger.info(f"Step Function Execution Response: {response}")

    return {
        "statusCode": 200,
        "body": json.dumps("Step Function execution started successfully."),
    }
