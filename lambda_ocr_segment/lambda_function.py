import json
from lambda_ocr_segment import ocr_segment
# Configure OpenAI API

def lambda_handler(event, context):
    try:
        # Get the image from the event
        if 'body' in event:
            # If the event contains a body (API Gateway)
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
            image_data = body.get('image')
        else:
            # Direct invocation
            image_data = event.get('image')

        # Process the image
        result = ocr_segment(image_data)

        return {
            'statusCode': 200,
            'body': json.dumps({
                'text': result
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }



