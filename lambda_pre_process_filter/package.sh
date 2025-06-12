#!/bin/bash


## this scrip is for manual create lambda function with zip file
# Ensure Poetry is properly configured with pyproject.toml
echo "Running poetry install and lock to update dependencies..."
poetry install
poetry lock  # Make sure the lockfile is up-to-date

# Clean up any existing package directory
rm -rf ./package
mkdir -p ./package
mkdir -p ./package/pipeline_utils/utils
poetry self add poetry-plugin-export
# Use Poetry to export and install dependencies into the package directory
echo "Exporting dependencies and installing to package directory..."
poetry export -f requirements.txt --without-hashes > requirements.txt

pip install -r requirements.txt --target ./package
cp -r ../database_service/ ./package/
# cp -r ../pipeline_utils/ ./package/
cp ../pipeline_utils/utils/__init__.py ./package/pipeline_utils/utils/
cp ../pipeline_utils/utils/log.py ./package/pipeline_utils/utils/
cp s3_load.py ./package/pipeline_utils/utils/
cp -r ../pipeline_utils/cfg/ ./package/pipeline_utils/
cp lambda_function.py ./package/
cp sheet_transfer_and_ocr.py ./package/
cp aws_ocr.py ./package/

cd package
zip -r ../${PACKAGE_ZIP_NAME}.zip .
cd ..

# Upload the zip file to S3
# export s3_dir="s3://deploy-test-wy/lambda_packages/"
echo "Uploading deployment package to S3..."
aws s3 cp $PACKAGE_ZIP_NAME.zip ${S3_DIR}${PACKAGE_ZIP_NAME}.zip
echo "Deployment package uploaded to ${s3_dir}"

# Clean up the requirements file
rm requirements.txt



