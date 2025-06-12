# OCR Segment Function

this module was for deploy a lambda function to ocr small pictures calling openai api
it requires AWS secret manager service to store the API key and
also requires the AWS lambda role having permission to access the AWS secret manager.

## Step 1 zip code and packages 
```angular2html
$ bash package.sh
```
then you will have a zip file \
`lambda_ocr_segment.zip`

## Step 2 Create Lambda function 
reference : https://docs.aws.amazon.com/lambda/latest/dg/configuration-function-zip.html \

1. Open the Functions page of the Lambda console.
2. Choose Create function.
3. Choose Author from scratch or Use a blueprint to create your function.
4. Under Basic information, do the following: \
   a. For Function name, enter the function name. Function names are limited to 64 characters in length. \
   b. For Runtime, choose the language version to use for your function.\
   c.(Optional) For Architecture, choose the instruction set architecture to use for your function. The default architecture is x86_64. When you build the deployment package for your function, make sure that it is compatible with this instruction set architecture.

5. (Optional) Under Permissions, expand Change default execution role. You can create a new Execution role or use an existing role.\
6. (Optional) Expand Advanced settings. You can choose a Code signing configuration for the function. You can also configure an (Amazon VPC) for the function to access. \
7. Choose Create function.

### Create function using AWS CLI (sample)
```angular2html
aws lambda create-function \
  --function-name MyFunction \
  --runtime python3.9 \
  --role arn:aws:iam::123456789012:role/lambda-role \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://function.zip

```

### AWS CloudFormation yaml file (sample)
This CloudFormation template:

Creates an IAM role with basic Lambda execution permissions \
Creates a Lambda function that uses your ZIP file stored in an S3 bucket \
Sets up configuration like memory, timeout, environment variables, etc. \
Exports the Lambda function ARN as an output \

if you did not defined the execition IAM role for lambda using this template
```angular2html
AWSTemplateFormatVersion: '2010-09-09'
Description: 'CloudFormation template for Lambda function'

Resources:
  LambdaExecutionRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: lambda.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

  MyLambdaFunction:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: MyFunction
      Handler: lambda_function.lambda_handler
      Role: !GetAtt LambdaExecutionRole.Arn
      Code:
        S3Bucket: my-lambda-bucket
        S3Key: function.zip
      Runtime: python3.9
      Timeout: 30
      MemorySize: 128
      Environment:
        Variables:
          ENV_VAR_1: value1
          ENV_VAR_2: value2

Outputs:
  LambdaFunctionArn:
    Description: ARN of the Lambda function
    Value: !GetAtt MyLambdaFunction.Arn

```

if you have defined the IAM role for executing the lambda function (recommended) using the following template
```angular2html
AWSTemplateFormatVersion: '2010-09-09'
Description: 'CloudFormation template for Lambda function using existing IAM role'

Resources:
  MyLambdaFunction:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: MyFunction
      Handler: lambda_function.lambda_handler
      Role: arn:aws:iam::123456789012:role/your-existing-lambda-role-name  # Replace with your actual role ARN
      Code:
        S3Bucket: my-lambda-bucket
        S3Key: function.zip
      Runtime: python3.9
      Timeout: 30
      MemorySize: 128
      Environment:
        Variables:
          ENV_VAR_1: value1
          ENV_VAR_2: value2

Outputs:
  LambdaFunctionArn:
    Description: ARN of the Lambda function
    Value: !GetAtt MyLambdaFunction.Arn
```
#### Deploy the cloud formation template
```angular2html
aws cloudformation deploy \
  --template-file template.yaml \
  --stack-name my-lambda-stack \
  --capabilities CAPABILITY_IAM
```

