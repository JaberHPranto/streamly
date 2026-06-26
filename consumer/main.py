import json

import boto3
from settings import Settings

settings = Settings()

sqs_client = boto3.client("sqs", region_name="ap-southeast-1")


def poll_sqs():
    while True:
        response = sqs_client.receive_message(
            QueueUrl=settings.SQS_VIDEO_PROCESSING_QUEUE_URL,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=10,
        )

        for message in response.get("Messages", []):
            message_body = json.loads(message["Body"])

            # Delete test events from the queue
            if (
                "Service" in message_body
                and "Event" in message_body
                and message_body.get("Event") == "s3:TestEvent"
            ):
                sqs_client.delete_message(
                    QueueUrl=settings.SQS_VIDEO_PROCESSING_QUEUE_URL,
                    ReceiptHandle=message["ReceiptHandle"],
                )
                continue

            # Process the message
            if "Record" in message_body:
                s3_record = message_body["Record"][0]["s3"]
                s3_bucket = s3_record["bucket"]["name"]
                s3_key = s3_record["object"]["key"]

                # Spin up a docker container


poll_sqs()
