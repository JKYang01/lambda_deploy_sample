import json
from aws_ocr import ocr_picture_text_only,get_detect_document_text
from sheet_transfer_and_ocr import search_schedule_keywords ,transfer_pdf_page_to_png
from database_service.init_db_instance_proxy import get_session
from database_service.crud import create_sheet_info


def lambda_handler(event, context):

    if 'body' in event:
        # If the event contains a body (API Gateway)
        body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        pdf_path = body.get('pdf_path')
        project_id = body.get('project_id')
        sheet_num = body.get('sheet_num')
    else:
        # Direct invocation
        pdf_path = event.get('pdf_path')
        project_id = event.get('project_id')
        sheet_num = event.get('sheet_num')

    try:
        sheet_data = {"project_id": project_id, "sheet_number": sheet_num, 'pdf_path': pdf_path, "pic_path": "",
                      "sheet_text_block":dict(),"sheet_text": [],
                      "ml_prediction": dict(), "have_drawing": False, "have_objects": False,
                      "have_symbol_legend": False, "have_schedule_table": False, "have_tag_target": False,
                      }

        # Process the image

        image_path, image_data = transfer_pdf_page_to_png(pdf_path)
        sheet_data['pic_path'] = image_path

        response = get_detect_document_text(image_data,from_s3=False)
        sheet_data['sheet_text_block'] = response['Blocks']

        result = ocr_picture_text_only(image_data, from_s3=False)
        sheet_data['sheet_text'] = result


        find_schedule_keywords = search_schedule_keywords(result)
        sheet_data['have_schedule_table'] = find_schedule_keywords
        with get_session() as session:
            new_sheet_info = create_sheet_info(session=session,sheet_data=sheet_data)
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'sheet_info_id': str(new_sheet_info.id)
                })
            }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }
