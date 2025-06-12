import boto3
from botocore.exceptions import ClientError
import json
import os

DEV = os.environ.get("DEV",False)
role_arn = os.environ.get("ROLE_ARN", "")
region = os.environ.get("AWS_REGION", "us-east-2")

def get_secret(secret_id):
    if DEV:
        base_session = boto3.session.Session()
        sts_client = base_session.client('sts')
        assumed_role = sts_client.assume_role(
            RoleArn =  role_arn,   # example "arn:aws:iam::<account number>:role/secrete_manager_access",
            RoleSessionName="AssumeRoleSession"
        )
        credentials = assumed_role['Credentials']

        # Create a new session with the role credentials
        session = boto3.session.Session(
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken'],
            region_name='us-east-2'
        )
        region_name = "us-east-2"
        client = session.client(
            service_name='secretsmanager',
            region_name=region_name,
        )
    else:
        session = boto3.Session(region_name=region)
        credentials = session.get_credentials()
        session = boto3.session.Session(
            aws_access_key_id=credentials.access_key,
            aws_secret_access_key=credentials.secret_key,
            region_name=region,
            aws_session_token=credentials.token
        )
        client = session.client(service_name="secretsmanager")

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_id
        )
        secret = json.loads(get_secret_value_response['SecretString'])
        return secret
    except ClientError as e:
        raise e