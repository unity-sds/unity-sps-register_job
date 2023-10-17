#!/usr/bin/env python
import boto3
import argparse
import json
import os
import regex


def parse_args():

    parser = argparse.ArgumentParser(description="Update job status and results")

    parser.add_argument("--job_id", type=str, help="Job ID of job being executed(required)")
    parser.add_argument("--update_status", type=str, help="Job status")
    parser.add_argument("--update_results", action='store_true', help="Update results")
    parser.add_argument("--aws_auth_method", type=str, default="iam")
    parser.add_argument("--jobs_data_sns_topic_arn", type=str, default="")

    args = parser.parse_args()

    if not args.update_status and not args.update_results:
        parser.error("Either --update_status or --update_results must be specified.")

    return parser.parse_args()


def get_sts_and_sns_clients(aws_auth_method):
    if aws_auth_method == "keys":
        sts_client = boto3.client(
            "sts",
            region_name="us-west-2",
            aws_access_key_id=os.getenv("ACCESS_KEY"),
            aws_secret_access_key=os.getenv("SECRET_KEY"),
            aws_session_token=os.getenv("SESSION_TOKEN"),
        )
        print(sts_client.get_caller_identity())
        client = boto3.client(
            "sns",
            region_name="us-west-2",
            aws_access_key_id=os.getenv("ACCESS_KEY"),
            aws_secret_access_key=os.getenv("SECRET_KEY"),
            aws_session_token=os.getenv("SESSION_TOKEN"),
        )

    elif aws_auth_method == "iam":
        sts_client = boto3.client("sts", region_name="us-west-2")
        print(sts_client.get_caller_identity())
        client = boto3.client("sns", region_name="us-west-2")

    else:
        print(f"Invalid aws_auth_method: {aws_auth_method}")
        print(f"Supported methods: iam, keys")
        exit()

    return sts_client, client


def find_output():
    """
    This function parses the stdout file and extracts the workflow output
    :return:
    """
    # open stdout file
    f = open("stdout.txt", "r")
    stdout = f.read()

    pattern = regex.compile(r'\{(?:[^{}]|(?R))*\}')
    json_found = pattern.findall(stdout)
    cwl_output = json.loads(json_found[-1])
    print(json.dumps(cwl_output, indent=2))
    # TODO: Make the keyword products dynamic
    if cwl_output.get("products") is not None:
        print("Job completed. Product successfully found.")
        job_status = "Succeeded"
        return job_status, cwl_output
    else:
        print("Job failed. Product not generated.")
        job_status = "Failed"
        return job_status, {}

def main():
    args = parse_args()

    # get sts and sns aws clients
    sts_client, sns_client = get_sts_and_sns_clients(args.aws_auth_method)

    # contstruct final job data json object
    job_data = {"id": args.job_id}
    if args.update_status:
        job_data["status"] = args.update_status
    if args.update_results:
        job_status, cwl_output = find_output()
        job_data["status"] = job_status
        job_data["outputs"] = cwl_output

    topic_arn = args.jobs_data_sns_topic_arn
    print(job_data)

    print(
        sns_client.publish(
            TopicArn=topic_arn, Message=json.dumps(job_data), MessageGroupId=args.job_id
        )
    )


if __name__ == "__main__":
    main()
