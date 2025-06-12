import re
from openai import OpenAI
from .get_keys import get_secret


API_KEY=get_secret("gpt_apikey")
client = OpenAI(
    api_key=API_KEY["gpt_ocr"]
)

def openai_image_content_extract(base64_image):
    """
    Sends the base64-encoded image to the OpenAI API and retrieves the extracted text.
    """
    # base64_image = encode_image(image)
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Extract the words and symbols in the image,\
                                if it is empty,return None \
                                Do not include any markdown or code formatting."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            },
                        },
                    ],
                }
            ],
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"\nError extracting text from image: {e}")
        return ''


def ocr_segment(base64_image):
    ocr_text = openai_image_content_extract(base64_image)
    return ocr_process_table_cell(ocr_text)



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

# def encode_image(image):
#     """
#     Encodes an image file to a base64 string.
#     """
#     try:
#         if isinstance(image, str) and os.path.isfile(image):
#             with open(image, "rb") as image_file:
#                 return base64.b64encode(image_file.read()).decode('utf-8')
#         elif isinstance(image, np.ndarray):
#             # It's already an image object
#             _, buffer = cv2.imencode('.png', image)
#             # Convert binary buffer to Base64 string
#             return base64.b64encode(buffer).decode('utf-8')
#
#     except Exception as e:
#         print(f"\nError encoding image: {e}")
#         return ""

