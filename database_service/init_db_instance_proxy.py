import os
import boto3
import json
import logging
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from contextlib import contextmanager
from botocore.config import Config

logger = logging.getLogger()
logger.setLevel(logging.INFO)
host = os.environ.get('PROXY_HOST')
port = os.environ.get('DB_PORT', 5432)
role_arn = os.environ.get('ROLE_ARN')
db_name = os.environ.get('DB_NAME')
region = os.environ.get('AWS_REGION')
secret_id = os.environ.get('SECRET_ID')  # os.environ['DB_USER_SECRET_ARN']
_db_conn = None

# Global connection and session factory
_engine = None
_session_factory = None

config = Config(
    connect_timeout=5,
    read_timeout=5
)
config.retries = {'max_attempts': 2}


def get_db_credentials():
    """Get database credentials from Secrets Manager with timeout handling"""

    try:
        base_session = boto3.Session(region_name=region)
        credentials = base_session.get_credentials()

        session = boto3.session.Session(
            aws_access_key_id=credentials.access_key,
            aws_secret_access_key=credentials.secret_key,
            region_name=region,
            aws_session_token=credentials.token
        )
        secrets_client = session.client(
            service_name="secretsmanager"
        )

        resp = secrets_client.get_secret_value(SecretId=secret_id)
        secret = json.loads(resp['SecretString'])

        return secret['username'], secret['password']
    except Exception as e:
        logger.error(f"Failed to get credentials: {str(e)}", exc_info=True)
        raise


def init_db(lazy=True):
    """Initialize database connection with lazy loading option"""
    global _engine, _session_factory

    # Return existing engine if already initialized and lazy loading is enabled
    if lazy and _engine is not None and _session_factory is not None:
        return _engine, _session_factory

    try:
        username, password = get_db_credentials()
        database_url = f"postgresql://{username}:{password}@{host}:{port}/{db_name}"
        # Create engine with optimized settings for Lambda
        _engine = create_engine(
            database_url,
            echo=False,  # Disable SQL logging
            pool_size=1,  # Minimal pool for Lambda
            max_overflow=2,  # Allow minimal overflow
            pool_timeout=5,  # Shorter timeout
            pool_pre_ping=True,  # Test connections
            pool_recycle=300,  # Recycle connections after 5 minutes
            connect_args={
                "sslmode": "require",
                "connect_timeout": 5,  # Reduced connection timeout
                "application_name": "lambda-function"  # For identification in logs
            }
        )
        _session_factory = sessionmaker(bind=_engine)
        return _engine, _session_factory
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}", exc_info=True)
        raise


@contextmanager
def get_session():
    """Context manager for database sessions with proper cleanup"""
    _, session_factory = init_db()
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database session error: {str(e)}", exc_info=True)
        raise
    finally:
        session.close()
