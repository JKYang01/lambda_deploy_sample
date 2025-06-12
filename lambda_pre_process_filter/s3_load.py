import boto3
import json
from pipeline_utils.utils import DEFAULT_CFG
from PIL import Image
from io import BytesIO
import os
from pipeline_utils.utils.log import setup_logger

region = os.environ.get('AWS_REGION', "us-east-2")
# Set up S3
s3 = boto3.client(service_name='s3',
                  region_name=region,
                  )

bucket_name = DEFAULT_CFG.bucket_name
logger = setup_logger()


def get_png_files_from_s3(bucket_name, folder_name):
    """
    Retrieves all PNG files from a specific folder in an S3 bucket.

    Args:
        bucket_name (str): The name of the S3 bucket.
        folder_name (str): The folder name within the bucket.

    Returns:
        list: A list of PNG file names found in the specified folder.
    """
    png_files = []

    # Make sure folder_name ends with a trailing slash if not empty
    if folder_name and not folder_name.endswith('/'):
        folder_name += '/'

    # Paginate through results in case there are many files
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(
        Bucket=bucket_name,
        Prefix=folder_name
    )

    # Process each page of results
    for page in pages:
        if 'Contents' in page:
            for obj in page['Contents']:
                key = obj['Key']
                if key == folder_name:
                    continue
                relative_path = key[len(folder_name):]
                # If there are no additional slashes, it's directly in the folder
                if '/' not in relative_path:
                    # Only include PNG files
                    if key.lower().endswith('.png'):
                        # Create the full S3 URI
                        s3_uri = f"s3://{bucket_name}/{key}"
                        png_files.append(s3_uri)
    return png_files


def download_model(model_path, local_path):
    bucket, key = check_link(model_path)
    if not os.path.exists(local_path):
        logger.info(f"Downloading model from s3://{bucket}/{key}")
        s3.download_file(bucket, key, local_path)
        logger.info("Model downloaded successfully")


def fetch_s3_object(bucket, key):
    response = s3.get_object(Bucket=bucket, Key=key)
    return response['Body'].read()


def check_link(image_url):
    bucket = None
    key = image_url
    if image_url.startswith("s3://"):
        bucket = image_url.split("//")[1].split("/")[0]
        key = "/".join(image_url.split("//")[1].split("/")[1:])
    elif image_url.startswith("https://"):
        parts = image_url.split(".s3")[0].split("//")
        if len(parts) > 1:
            bucket = parts[1]
            key = image_url.split(bucket + ".s3.amazonaws.com/")[1]
    return bucket, key


def create_s3_directory(bucket_name, directory_name):
    _, directory_name = check_link(directory_name)
    if not directory_name.endswith('/'):
        directory_name += '/'
    try:
        s3.head_object(Bucket=bucket_name, Key=directory_name)
    except:
        try:
            s3.put_object(Bucket=bucket_name, Key=directory_name, Body='')
        except Exception as e:
            logger.error(f"Error occur when creating s3 directory {e}", exc_info=True)


def upload_json_to_s3(file_dir, json_data, bucket=None):
    if not bucket:
        bucket = bucket_name
    dir = os.path.dirname(file_dir)
    create_s3_directory(bucket, dir)
    try:
        json_string = json.dumps(json_data)
        s3.put_object(Bucket=bucket, Key=file_dir, Body=json_string)
        logger.info(f"Image successfully uploaded to {file_dir} in bucket {bucket_name}.")
    except Exception as e:
        logger.error(f"Failed to upload json to S3 {e}", exc_info=True)


def upload_img_to_s3(directory_name, img_data, img_name, bucket=None):
    if not bucket:
        bucket = bucket_name
    # The full path where the image will be stored
    if not directory_name.endswith('/'):
        directory_name += '/'
    img_path = f"{directory_name}{img_name}"
    create_s3_directory(bucket, directory_name)
    try:
        # Convert the PIL Image to bytes in PNG format
        img_byte_arr = BytesIO()
        img_data.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        s3.put_object(Bucket=bucket, Key=img_path, Body=img_byte_arr, ContentType='image/png')
        logger.info(f"Image successfully uploaded to {img_path} in bucket {bucket}.")
    except Exception as error:
        logger.error(f"Failed to upload image to S3 {error}", exc_info=True)


def upload_pdf_to_s3(directory_name, pdf_data, pdf_name, bucket=None):
    if not bucket:
        bucket = bucket_name
    pdf_path = f"{directory_name}/{pdf_name}"
    create_s3_directory(bucket, directory_name)
    new_bytes = pdf_data.write()
    try:
        s3.put_object(Bucket=bucket, Key=pdf_path, Body=new_bytes)
        logger.info(f" upload {pdf_path}")
    except  Exception as error:
        logger.error("Failed to upload pdf to S3", exc_info=True)


def upload_file_to_s3(file_name, object_name=None, bucket=None):
    if not bucket:
        bucket = bucket_name
    """
    Upload a file to an S3 bucket

    :param file_name: File to upload
    :param bucket_name: Bucket to upload to
    :param object_name: S3 object name. If not specified, file_name is used
    :return: True if file was uploaded, else False
    """
    if object_name is None:
        object_name = file_name

    # Upload the file
    try:
        s3.upload_file(file_name, bucket, object_name)
        print(f"uploaded {file_name} to {object_name} in bucket {bucket}")
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return False
    return True


def copy_file_in_s3(source_key, destination_key, bucket=None):
    """
    Copy a file within an S3 bucket from source_key to destination_key.
    """
    s3 = boto3.client('s3')
    copy_source = {
        'Bucket': bucket,
        'Key': source_key
    }
    s3.copy(copy_source, bucket, destination_key)


def pdf_from_s3(pdf_path):
    bucket, pdf_s3_key = check_link(pdf_path)
    pdf_file_obj = s3.get_object(Bucket=bucket, Key=pdf_s3_key)
    pdf_stream = pdf_file_obj['Body'].read()
    return pdf_stream


def img_from_s3(image_url):
    # download image file from s3
    bucket, key = check_link(image_url)
    data = fetch_s3_object(bucket, key)
    return Image.open(BytesIO(data))


def json_from_s3(s3_folder, file_name, bucket_name=bucket_name):
    # Download the pre annotation file (json format)
    key = f"{s3_folder}/{file_name}"
    data = fetch_s3_object(bucket_name, key)
    data_decode = data.decode("utf-8")
    return json.loads(data_decode)


def rename_file(input_bucket_name: str = None,
                old_file_name: str = None,
                new_file_name: str = None):
    # Define bucket name and object details
    if input_bucket_name is None:
        input_bucket_name = bucket_name

    # Copy the object to a new key (rename)
    s3.copy_object(
        Bucket=input_bucket_name,
        CopySource={'Bucket': input_bucket_name, 'Key': old_file_name},
        Key=new_file_name
    )

    # Delete the old object
    s3.delete_object(Bucket=bucket_name, Key=old_file_name)

