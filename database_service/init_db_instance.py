import boto3
import psycopg2
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from database_service.models import Base
from botocore.exceptions import ClientError
import logging
import json
import os

db_name = os.environ.get('DB_NAME', 'postgres')
db_instance_name=os.environ.get('DB_INSTANCE_NAME')
role_arn=os.environ.get('ROLE_ARN')
secret_id=os.environ.get('SECRET_ID')
DEV=os.environ.get('DEV','false').lower() == 'true'
region=os.environ.get('AWS_REGION','us-east-2')
_DB_INITIALIZED = False


def get_secret():
    if DEV:
        # using user account role to access service, dev only
        base_session = boto3.session.Session()
        sts_client = base_session.client('sts')
        assumed_role = sts_client.assume_role(
            RoleArn = role_arn,
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
        base_session = boto3.Session(region_name=region)
        credentials = base_session.get_credentials()
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

def get_rds():
    if DEV:
        base_session = boto3.session.Session()
        sts_client = base_session.client('sts')
        assumed_role = sts_client.assume_role(
        RoleArn = role_arn,
        RoleSessionName="AssumeRoleSession"
        )
        credentials = assumed_role['Credentials']
        session = boto3.session.Session(
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken'],
            region_name='us-east-2'
        )
        client = session.client(service_name="rds")

    else:
        session = boto3.Session(region_name=region)
        credentials = session.get_credentials()
        session = boto3.session.Session(
            aws_access_key_id=credentials.access_key,
            aws_secret_access_key=credentials.secret_key,
            region_name=region,
            aws_session_token= credentials.token
        )
        client = session.client(service_name="rds")

    return client


# Then use credentials like this
credentials = get_secret()
username = credentials['username']
password = credentials['password']


def init_rds_database():
    global _DB_INITIALIZED

    if _DB_INITIALIZED:
        return True
        # First, check if the RDS instance already exists
    rds = get_rds()
    try:
        # Check if the DB instance exists
        # If we get here, the instance exists, but we need to check if our database exists
        # Unfortunately, RDS API doesn't provide a direct way to list databases within an instance
        # We'll need to connect to the instance and check
        response = rds.describe_db_instances(
            DBInstanceIdentifier=db_instance_name
        )
        host = response['DBInstances'][0]['Endpoint']['Address']
        port = response['DBInstances'][0]['Endpoint']['Port']

        # For Lambda, we could use a simple check by attempting to connect to the database
        try:
            # Get connection parameters (should be from environment variables or secrets manager)
            logging.info(f"try to connet to RDS instance '{db_name}'")
            # Try to connect to the specific database
            conn = psycopg2.connect(
                dbname=db_name,
                user=username,
                password=password,
                host=host,
                port=port
            )
            conn.close()
            _DB_INITIALIZED = True
            # print(f"Database '{db_name}' already exists. Skipping creation.")
            return True
        except Exception as e:
            logging.error(f"Error connecting to PostgreSQL: {e}")
            return False

    except Exception as e:
        # The DB instance doesn't exist
        logging.error(f"Error checking RDS instance: {e}")
        return False



def init_db():
    # Initialize RDS database if needed
    db_initialized = init_rds_database()
    if db_initialized:

        try:
            rds = get_rds()
            response = rds.describe_db_instances(
                DBInstanceIdentifier=db_instance_name
            )
            host = response['DBInstances'][0]['Endpoint']['Address']
            port = response['DBInstances'][0]['Endpoint']['Port']

            # Get connection parameters (should be from environment variables)
            database_url = f"postgresql://{username}:{password}@{host}:{port}/{db_name}"

            # Initialize engine
            engine = create_engine(database_url,pool_size=1000,max_overflow=0)

            # Create tables based on your models
            Base.metadata.create_all(bind=engine)

            return True
            # return engine, sessionmaker(autocommit=False, autoflush=False, bind=engine)

        except ClientError as e:
            raise e
    else:
        return False


# get db through proxy
# engine, SessionLocal = init_db()

# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()