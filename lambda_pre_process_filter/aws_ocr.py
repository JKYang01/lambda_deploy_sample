import os
import re
import io
import sys
import logging
from pipeline_utils.utils import ROOT, TEXTRACT_CLIENT
from pipeline_utils.utils.s3_load import upload_file_to_s3, check_link, fetch_s3_object

def get_detect_document_text(image, from_s3=False):
    if from_s3:
        if isinstance(image, str):
            bucket_name, key = check_link(image)
            response = TEXTRACT_CLIENT.detect_document_text(Document={'S3Object': {
                'Bucket': bucket_name,
                'Name': key}
            })

        else:  # the image is already loaded by img_from_s3
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            bytes_data = bytearray(buffer.getvalue())
            response = TEXTRACT_CLIENT.detect_document_text(Document={'Bytes': bytes_data})
    else:
        try:
            if isinstance(image, str) and os.path.isfile(image):
                with open(image, "rb") as image_file:
                    image_data = image_file.read()
                    bytes_data = bytearray(image_data)
            elif "PIL.Image.Image" in str(type(image)) or hasattr(image, "save"):
                buffer = io.BytesIO()
                image.save(buffer, format="PNG")
                bytes_data = buffer.getvalue()

            else:
                logging.error(f'unknown image data type {file_name}')
                return

        except Exception as e:
            logging.error(f'Error occured while processing in ocr step {file_name}: {e}')
            return

        response = TEXTRACT_CLIENT.detect_document_text(Document={'Bytes': bytes_data})
    return response


def ocr_picture_text_only(image, from_s3=False):
    response = get_detect_document_text(image, from_s3=from_s3)
    blocks = response['Blocks']
    ocr_results = []
    for block in blocks:
        if block['BlockType'] == "LINE":
            ocr_results.append(block["Text"])
    return ocr_results


def ocr_process_table_cell(ocr_text):
    ocr_text = re.sub(r'^None$', "", ocr_text)
    ocr_text = re.sub(r'^\"\"$', "", ocr_text)
    ocr_text = re.sub(r"None", "", ocr_text)
    ocr_text = re.sub(r"I[0Oo]I|\|[0Oo]\|", "101", ocr_text)
    ocr_text = re.sub(r"[\u2205\u00D8\u2300]", "", ocr_text)
    ocr_text = re.sub(r"￠", "", ocr_text)
    ocr_text = re.sub(r"Å", "A", ocr_text)
    ocr_text = re.sub(r"\|\|\|", "111", ocr_text)
    ocr_text = re.sub(r"\|\|", "11", ocr_text)
    ocr_text = re.sub(r"^<$", "K", ocr_text)
    ocr_text = re.sub(r"^q$", "9", ocr_text)
    ocr_text = re.sub(r"\xC2|\xA0|~|\n\x0c", "", ocr_text)
    return ocr_text


def get_rows_columns_map(table_result, blocks_map):
    rows = {}
    scores = []
    for relationship in table_result['Relationships']:
        if relationship['Type'] == 'CHILD':
            for child_id in relationship['Ids']:
                cell = blocks_map[child_id]
                if cell['BlockType'] == 'CELL':
                    row_index = cell['RowIndex']
                    col_index = cell['ColumnIndex']
                    if row_index not in rows:
                        # create new row
                        rows[row_index] = {}

                    # get confidence score
                    scores.append(str(cell['Confidence']))
                    # get the text value
                    cell_text = get_text(cell, blocks_map)
                    cell_text = ocr_process_table_cell(cell_text)
                    rows[row_index][col_index] = cell_text  # get_text(cell, blocks_map)
    return rows, scores


def get_text(result, blocks_map):
    text = ''
    if 'Relationships' in result:
        for relationship in result['Relationships']:
            if relationship['Type'] == 'CHILD':
                for child_id in relationship['Ids']:
                    word = blocks_map[child_id]
                    if word['BlockType'] == 'WORD':
                        if "," in word['Text'] and word['Text'].replace(",", "").isnumeric():
                            text += '"' + word['Text'] + '"' + ' '
                        else:
                            text += word['Text'] + ' '
                    if word['BlockType'] == 'SELECTION_ELEMENT':
                        if word['SelectionStatus'] == 'SELECTED':
                            text += 'X '
    return text


def get_table_title(table_result, blocks_map):
    title_ids = []
    try:
        for relationship in table_result['Relationships']:
            if relationship['Type'] == 'TABLE_TITLE':
                title_ids.extend(relationship['Ids'])
    except Exception as e:
        print(table_result)
        logging.error(f"process error during gettable title{e}")
        title_ids = []

    if title_ids:
        title = ''
        for title_id in title_ids:
            title_result = blocks_map[title_id]
            if 'Relationships' in title_result:
                for relationship in title_result['Relationships']:
                    if relationship['Type'] == 'CHILD':
                        for child_id in relationship['Ids']:
                            title_cell = blocks_map[child_id]
                            if title_cell['BlockType'] == 'WORD' or title_cell['BlockType'] == 'LINE':
                                cell_text = title_cell['Text']
                                title += cell_text + ' '
            else:
                title += ' '
                logging.info("not find title line")

    else:
        title = 'no_title'

    return title


def get_document_analyze(file_name, from_s3=False):
    if from_s3:
        bucket, key = check_link(file_name)
        img_data = fetch_s3_object(bucket, key)
        bytes_data = bytearray(img_data)
        logging.info(f'Image loaded {file_name}')
    else:
        with open(file_name, 'rb') as file:
            img_test = file.read()
            bytes_data = bytearray(img_test)
            logging.info(f'Image loaded {file_name}')
    response = TEXTRACT_CLIENT.analyze_document(Document={'Bytes': bytes_data}, FeatureTypes=['TABLES'])

    return response


def get_table_blocks(response):
    blocks = response['Blocks']
    # pprint(blocks)
    blocks_map = {}
    table_blocks = []
    for block in blocks:
        blocks_map[block['Id']] = block
        if block['BlockType'] == "TABLE":
            table_blocks.append(block)

    if len(table_blocks) <= 0:
        return "No_table", "{}"

    return table_blocks, blocks_map


def extract_table_csv(response,s3_save_address,temp_dir=ROOT/'temp'):
    # Get the text blocks
    table_blocks, blocks_map = get_table_blocks(response)
    csv_name_list = []
    for index, table in enumerate(table_blocks):
        title_text = get_table_title(table, blocks_map)
        csv_name = generate_table_csv(table, blocks_map, index + 1, title_text, s3_save_address,temp_dir=temp_dir)
        csv_name_list.append(csv_name)

    return csv_name_list


def generate_table_csv(table_result, blocks_map, table_index, title_txt, s3_save_address, temp_dir):
    '''
    s3_save_address is the directory where the table is located on s3 bucket
    '''
    rows, _ = get_rows_columns_map(table_result, blocks_map)
    bucket, key = check_link(s3_save_address)

    table_id = 'Table_' + str(table_index) + "_" + title_txt

    # get cells.
    csv_name = '{0}.csv'.format(table_id)
    csv = ''
    for row_index, cols in rows.items():
        for col_index, text in cols.items():
            # col_indices = len(cols.items())
            csv += '{}'.format(text) + ","
        csv += '\n'

    with open(temp_dir/csv_name, 'wt') as file:
        file.write(csv)
    try:
        upload_file_to_s3(temp_dir / csv_name, object_name=key + "/" + csv_name, bucket=bucket)
        # os.remove(temp_dir/csv_name) # uncomment when deploy to cloud
    except Exception as e:
        logging.error("Failed to upload csv to S3", exc_info=True)

    return f"s3://{bucket}/{key}/{csv_name}"


def main(file_name, s3_save_address,temp_dir=ROOT/'temp'):
    response = get_document_analyze(file_name)
    csv_address_list = extract_table_csv(response, s3_save_address, temp_dir=temp_dir)
    logging.info(f'CSV OUTPUT FILE: {csv_address_list}')


if __name__ == "__main__":
    file_name = sys.argv[1]
    s3_save_address = sys.argv[2]
    main(file_name, s3_save_address)
