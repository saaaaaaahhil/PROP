import base64
import uuid
from routes.llm_connections import openai_client
import fitz
import os
from routes.images.store_operations import upload_image_to_store
from routes.mongo_db_functions import update_mongo_file_status
from datetime import datetime
from pathlib import Path

def upload_image(contents, project_id: str):
    """
    This function extracts the relevant images from the pdf file and stores in database
    """
    try:
        # Open the document
        doc = fitz.open("pdf", contents)
        images = []

        # Create the temp directory if it does not exist
        temp_dir = Path("temp")
        temp_dir.mkdir(parents=True, exist_ok=True)

        for page in doc:  # iterate through the pages
            pix = page.get_pixmap()  # render page to an image
            image_id = str(uuid.uuid4())
            pix.save(f'temp/{image_id}.png') # Save file in temp directory
            images.append(f"{image_id}")

        # Process each image
        for image in images:
            encoded_image = encode_image(f'temp/{image}.png')
            base64_image = encoded_image.get('encoded') # Get encoded image string
            image_content = encoded_image.get('content') # Get image content
            image_name = get_image_name(base64_image)
            # If image is relevant then store it in database
            if image_name != 'invalid_image':    
                update_mongo_file_status({'_id': image, 'project_id': project_id}, {"$set": {'file_name': image_name, 'file_type': 'png', 'file_size': f'{0} KB', "added_on": datetime.now().isoformat(), 'chunks': [], 'status': 'in_progress'}}, True)
                upload_image_to_store(project_id, image_content, image_name, 'image/png')
            os.remove(f'temp/{image}.png') # Delete temporarily stored images

    except Exception as e:
       print(f'Error getting images: {e}')

        

def get_image_name(base64_image):
    """
    This function retrieves the name of the image based on its context.
    """
    try:
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": """Study the image and suggest me a proper as specific name as possible according to context of the image. I want to save image name as a meaningful name so i want to  name it according to its context. Return a more detailed name. Name of the image should be little bit like a description in one line.You need to keep one more thing in mind, do not put spaces between two words, you join words with underscore. Do not give name with spaces, replace all spaces with underscore. If the image is related to floor plan of some particular units or site map of property or location map(in traditional map view) of property then return its name according to its context otherwise return invalid_image as it's name. If image seem's invalid or other than floor plan or sitemap or traditional location map view then just return invalid image don't provide any additional information. 
                        
                        Examples:
                            1. If the image contains floor plans for 4 bed and 5 bed units, then ideal name for file would contain both bed unit types.
                            2. If the image contains panoramic or wide-angle view of the neighborhood then return invalid_image.

                        """
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}"
                    }
                } 
            ]
            }
        ]
        response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=300,
                temperature=0.5)
        image_name = response.choices[0].message.content
        print(image_name)
        return image_name
    except Exception as e:
       raise Exception(f'Error generating file name: {e}')


def encode_image(image_path):
  with open(image_path, "rb") as image_file:
    image_content = image_file.read()
    return {'encoded': base64.b64encode(image_content).decode('utf-8'), 'content': image_content}