import re
import os
import fitz
from PIL import Image
from pipeline_utils.utils import extract_filename_without_suffix
from pipeline_utils.utils.s3_load import (upload_img_to_s3,
                                          pdf_from_s3,
                                          check_link)
import logging

first_degree_filter = ["schedule","schedules"]
second_degree_filter = ["door","doors","door type","door types","frame","frames","material","door number"]


def search_schedule_keywords(text_list):
    first_filter = re.compile('|'.join(re.escape(keyword) for keyword in first_degree_filter ))
    second_filter = re.compile('|'.join(re.escape(keyword) for keyword in second_degree_filter ))
    for text in text_list:
        if first_filter.search(text.lower()) and second_filter.search(text.lower()):
            return True
    return False


def transfer_pdf_page_to_png(pdf_s3_path):
    try:
        pdf_name = extract_filename_without_suffix(pdf_s3_path)
        bucket, pdf_s3 = check_link(pdf_s3_path)
        pdf_folder_s3 = os.path.dirname(pdf_s3)
        output_directory = f"{pdf_folder_s3}"
        pdf_stream = pdf_from_s3(pdf_s3_path)
        # Open the PDF with fitz
        doc = fitz.open(stream=pdf_stream, filetype="pdf")
        page = doc[0]
        pix = page.get_pixmap()
        # Convert the pixmap to a PIL Image
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        upload_img_to_s3(output_directory, img, f"{pdf_name}.png", bucket=bucket)
        doc.close()
        return f"s3://{bucket}/{output_directory}/{pdf_name}.png", img
    except Exception as e:
        logging.error(e, exc_info=True)
        return None, None

