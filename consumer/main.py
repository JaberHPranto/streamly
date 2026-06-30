import json

import boto3
from settings import Settings

settings = Settings()

sqs_client = boto3.client("sqs", region_name="ap-southeast-1")
ecs_client = boto3.client("ecs", region_name="ap-southeast-1")


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

            print(message_body)

            # Process the message
            if "Records" in message_body:
                print("===== TASK CREATED ======")
                s3_record = message_body["Records"][0]["s3"]
                s3_bucket = s3_record["bucket"]["name"]
                s3_key = s3_record["object"]["key"]

                response = ecs_client.run_task(
                    cluster="arn:aws:ecs:ap-southeast-1:442042517999:cluster/stremly-transcoder-cluster",
                    launchType="FARGATE",
                    # static task definition (blueprint) — defines container image, CPU/memory, IAM role, command.
                    taskDefinition="arn:aws:ecs:ap-southeast-1:442042517999:task-definition/video-transcoder-job:6",
                    # dynamic overrides — injects per-video env vars (S3_BUCKET, S3_KEY)
                    overrides={
                        "containerOverrides": [
                            {
                                "name": "streamly-transcoder",  # container name in task definition
                                "environment": [
                                    {"name": "S3_BUCKET", "value": s3_bucket},
                                    {"name": "S3_KEY", "value": s3_key},
                                ],
                            }
                        ]
                    },
                    # wires the container into the VPC
                    networkConfiguration={
                        "awsvpcConfiguration": {
                            "subnets": [
                                "subnet-05e3355319dc7b7e3",
                                "subnet-03dda126e9a5609d1",
                                "subnet-07f221993ce8677df",
                            ],
                            "assignPublicIp": "ENABLED",
                            "securityGroups": ["sg-0ed9ef5a1b590404f"],
                        }
                    },
                )

                print(response)

                sqs_client.delete_message(
                    QueueUrl=settings.SQS_VIDEO_PROCESSING_QUEUE_URL,
                    ReceiptHandle=message["ReceiptHandle"],
                )


poll_sqs()
